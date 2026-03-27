"""
할머니 말벗 AI Agent - 음성 파이프라인
STT (Whisper) + TTS (Google/CLOVA) + 오디오 입출력
"""
from __future__ import annotations

import io
import wave
import struct
import logging
import tempfile
from pathlib import Path

from config.settings import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    AUDIO_CHUNK_SIZE,
    SILENCE_THRESHOLD,
    SILENCE_DURATION,
    WHISPER_MODEL,
    WHISPER_LANGUAGE,
    TTS_PROVIDER,
    TTS_LANGUAGE,
    TTS_VOICE_NAME,
    TTS_SPEAKING_RATE,
    TTS_PITCH,
    GOOGLE_TTS_API_KEY,
    CLOVA_CLIENT_ID,
    CLOVA_CLIENT_SECRET,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# STT (Speech-to-Text) - Whisper
# ─────────────────────────────────────────────

class WhisperSTT:
    """OpenAI Whisper 기반 음성→텍스트 변환"""

    def __init__(self, model_name: str = WHISPER_MODEL):
        self.model_name = model_name
        self.model = None

    def load_model(self):
        """Whisper 모델 로드 (최초 1회)"""
        try:
            import whisper
            logger.info("Whisper 모델 로딩: %s", self.model_name)
            self.model = whisper.load_model(self.model_name)
            logger.info("Whisper 모델 로딩 완료")
        except ImportError:
            logger.error("openai-whisper 패키지가 설치되지 않았습니다.")
            raise

    def transcribe(self, audio_path: str) -> str:
        """
        오디오 파일을 텍스트로 변환

        Args:
            audio_path: WAV 파일 경로

        Returns:
            변환된 텍스트
        """
        if self.model is None:
            self.load_model()

        result = self.model.transcribe(
            audio_path,
            language=WHISPER_LANGUAGE,
            fp16=False,  # 라즈베리파이 CPU 호환
        )
        text = result["text"].strip()
        logger.info("STT 결과: %s", text)
        return text

    def transcribe_from_bytes(self, audio_bytes: bytes) -> str:
        """바이트 데이터에서 직접 변환"""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            tmp.write(audio_bytes)
            tmp.flush()
            return self.transcribe(tmp.name)


# ─────────────────────────────────────────────
# TTS (Text-to-Speech)
# ─────────────────────────────────────────────

class BaseTTS:
    """TTS 기본 인터페이스"""

    def synthesize(self, text: str) -> bytes:
        """텍스트를 음성 바이트로 변환"""
        raise NotImplementedError


class GoogleTTS(BaseTTS):
    """Google Cloud TTS"""

    def synthesize(self, text: str) -> bytes:
        """Google Cloud TTS로 음성 합성"""
        try:
            from google.cloud import texttospeech
        except ImportError:
            logger.error("google-cloud-texttospeech 패키지가 설치되지 않았습니다.")
            raise

        client = texttospeech.TextToSpeechClient()

        input_text = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=TTS_LANGUAGE,
            name=TTS_VOICE_NAME,
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=TTS_SPEAKING_RATE,
            pitch=TTS_PITCH,
            sample_rate_hertz=AUDIO_SAMPLE_RATE,
        )

        response = client.synthesize_speech(
            input=input_text,
            voice=voice,
            audio_config=audio_config,
        )

        logger.info("Google TTS 합성 완료: %d bytes", len(response.audio_content))
        return response.audio_content


class ClovaTTS(BaseTTS):
    """NAVER CLOVA Voice TTS"""

    API_URL = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"

    def synthesize(self, text: str) -> bytes:
        """CLOVA Voice로 음성 합성"""
        import requests

        headers = {
            "X-NCP-APIGW-API-KEY-ID": CLOVA_CLIENT_ID,
            "X-NCP-APIGW-API-KEY": CLOVA_CLIENT_SECRET,
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "speaker": "nara",  # 한국어 여성 음성
            "text": text,
            "volume": "0",
            "speed": "0",  # -5 ~ 5 (느리게 ~ 빠르게)
            "pitch": "0",
            "format": "wav",
        }

        response = requests.post(self.API_URL, headers=headers, data=data, timeout=10)

        if response.status_code == 200:
            logger.info("CLOVA TTS 합성 완료: %d bytes", len(response.content))
            return response.content
        else:
            logger.error("CLOVA TTS 오류: %s", response.text)
            raise RuntimeError(f"CLOVA TTS 오류: {response.status_code}")


class FallbackTTS(BaseTTS):
    """오프라인 대체 TTS (pyttsx3 사용)"""

    def synthesize(self, text: str) -> bytes:
        """로컬 TTS 엔진으로 합성"""
        try:
            import pyttsx3
        except ImportError:
            logger.error("pyttsx3 패키지가 설치되지 않았습니다.")
            raise

        engine = pyttsx3.init()
        engine.setProperty("rate", 130)  # 느린 속도

        # 임시 파일로 저장 후 바이트 반환
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
            engine.save_to_file(text, tmp.name)
            engine.runAndWait()
            return Path(tmp.name).read_bytes()


def get_tts_engine() -> BaseTTS:
    """설정에 따른 TTS 엔진 반환"""
    engines = {
        "google": GoogleTTS,
        "clova": ClovaTTS,
        "fallback": FallbackTTS,
    }
    engine_class = engines.get(TTS_PROVIDER, FallbackTTS)
    return engine_class()


# ─────────────────────────────────────────────
# 오디오 녹음/재생
# ─────────────────────────────────────────────

class AudioRecorder:
    """마이크 입력을 녹음하고 침묵을 감지하는 클래스"""

    def __init__(self):
        self._pyaudio = None

    def _get_pyaudio(self):
        if self._pyaudio is None:
            import pyaudio
            self._pyaudio = pyaudio.PyAudio()
        return self._pyaudio

    def record_until_silence(self) -> bytes | None:
        """
        마이크에서 녹음, 발화 후 침묵 감지되면 종료

        Returns:
            WAV 형식 바이트 데이터, 또는 발화가 없으면 None
        """
        import pyaudio

        pa = self._get_pyaudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=AUDIO_CHANNELS,
            rate=AUDIO_SAMPLE_RATE,
            input=True,
            frames_per_buffer=AUDIO_CHUNK_SIZE,
        )

        logger.info("녹음 시작... (침묵 감지 시 자동 종료)")

        frames = []
        silence_frames = 0
        has_speech = False
        silence_frame_limit = int(SILENCE_DURATION * AUDIO_SAMPLE_RATE / AUDIO_CHUNK_SIZE)

        try:
            while True:
                data = stream.read(AUDIO_CHUNK_SIZE, exception_on_overflow=False)
                frames.append(data)

                # RMS 계산 (볼륨 레벨)
                rms = self._calculate_rms(data)

                if rms > SILENCE_THRESHOLD:
                    has_speech = True
                    silence_frames = 0
                else:
                    silence_frames += 1

                # 발화 후 침묵이 지속되면 종료
                if has_speech and silence_frames > silence_frame_limit:
                    logger.info("침묵 감지 → 녹음 종료")
                    break

                # 최대 30초
                if len(frames) > (30 * AUDIO_SAMPLE_RATE // AUDIO_CHUNK_SIZE):
                    logger.info("최대 녹음 시간 도달")
                    break

        finally:
            stream.stop_stream()
            stream.close()

        if not has_speech:
            return None

        # WAV 형식으로 변환
        return self._frames_to_wav(frames)

    @staticmethod
    def _calculate_rms(data: bytes) -> float:
        """오디오 프레임의 RMS(볼륨) 계산"""
        count = len(data) // 2
        shorts = struct.unpack(f"{count}h", data)
        sum_squares = sum(s * s for s in shorts)
        return (sum_squares / count) ** 0.5

    @staticmethod
    def _frames_to_wav(frames: list[bytes]) -> bytes:
        """PCM 프레임을 WAV 바이트로 변환"""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(AUDIO_CHANNELS)
            wf.setsampwidth(2)  # 16bit = 2 bytes
            wf.setframerate(AUDIO_SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()

    def cleanup(self):
        """리소스 정리"""
        if self._pyaudio:
            self._pyaudio.terminate()
            self._pyaudio = None


class AudioPlayer:
    """스피커로 음성 출력"""

    def play_wav(self, wav_bytes: bytes):
        """WAV 바이트 데이터를 스피커로 재생"""
        import pyaudio

        buf = io.BytesIO(wav_bytes)
        with wave.open(buf, "rb") as wf:
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pa.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
            )
            try:
                chunk = 1024
                data = wf.readframes(chunk)
                while data:
                    stream.write(data)
                    data = wf.readframes(chunk)
            finally:
                stream.stop_stream()
                stream.close()
                pa.terminate()

    def play_text(self, text: str, tts_engine: BaseTTS | None = None):
        """텍스트를 음성으로 변환 후 재생"""
        if tts_engine is None:
            tts_engine = get_tts_engine()

        audio_bytes = tts_engine.synthesize(text)
        self.play_wav(audio_bytes)
