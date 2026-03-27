#!/usr/bin/env python3
"""
🧸 for-grandmother — 할머니 말벗 AI Agent
메인 애플리케이션

실행 방법:
    # 음성 모드 (라즈베리파이 + 마이크 + 스피커)
    python main.py

    # 텍스트 모드 (개발/테스트용)
    python main.py --text

    # 텍스트 모드 + 음성 출력
    python main.py --text --speak
"""

import argparse
import logging
import signal
import sys
import time
import threading
from datetime import datetime

# 프로젝트 루트를 경로에 추가
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))

from config.settings import SESSION_TIMEOUT
from src.memory import MemoryManager
from src.conversation import ConversationEngine
from src.notifier import TelegramNotifier
from src.hardware import HardwareController, TextInputSimulator

logger = logging.getLogger("grandmother")


class GrandmotherAgent:
    """할머니 말벗 AI Agent 메인 클래스"""

    def __init__(self, text_mode: bool = False, speak: bool = False):
        self.text_mode = text_mode
        self.speak = speak
        self._running = False
        self._in_conversation = False
        self._last_activity = time.time()

        # 모듈 초기화
        logger.info("🧸 할머니 말벗 에이전트 초기화...")
        self.memory = MemoryManager()
        self.memory.init_default_profile()
        self.engine = ConversationEngine(self.memory)
        self.notifier = TelegramNotifier()
        self.hardware = HardwareController()

        # 음성 모듈 (필요 시)
        self.stt = None
        self.tts_engine = None
        self.recorder = None
        self.player = None

        if not text_mode:
            self._init_audio()

        logger.info("✅ 초기화 완료!")

    def _init_audio(self):
        """음성 모듈 초기화"""
        try:
            from src.audio import WhisperSTT, AudioRecorder, AudioPlayer, get_tts_engine
            self.stt = WhisperSTT()
            self.stt.load_model()
            self.recorder = AudioRecorder()
            self.player = AudioPlayer()
            self.tts_engine = get_tts_engine()
            logger.info("음성 모듈 초기화 완료")
        except Exception as e:
            logger.error("음성 모듈 초기화 실패: %s", e)
            logger.info("텍스트 모드로 전환합니다.")
            self.text_mode = True

    # ─────────────────────────────────────────
    # 메인 루프
    # ─────────────────────────────────────────
    def run(self):
        """에이전트 메인 루프"""
        self._running = True

        # 시그널 핸들러 (Ctrl+C)
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        print()
        print("=" * 50)
        print("  🧸 할머니 말벗 에이전트")
        print("  모드:", "텍스트" if self.text_mode else "음성")
        print("=" * 50)
        print()

        if self.text_mode:
            self._run_text_mode()
        else:
            self._run_voice_mode()

    def _run_text_mode(self):
        """텍스트 모드 메인 루프"""
        simulator = TextInputSimulator()
        print("💬 텍스트 모드로 시작합니다.")
        print("   '종료' 또는 'quit'를 입력하면 종료됩니다.")
        print()

        # 첫 인사
        greeting = self.engine.generate_proactive_greeting("morning")
        print(f"🧸: {greeting}")
        self._speak_if_enabled(greeting)
        print()

        while self._running:
            user_input = simulator.get_input()

            if user_input is None:
                self._end_session()
                break

            # 대화 처리
            response = self.engine.chat(user_input)
            print(f"🧸: {response}")
            self._speak_if_enabled(response)
            print()

            # 긴급 키워드 체크 & 알림
            self._check_and_notify(user_input)

            self._last_activity = time.time()

    def _run_voice_mode(self):
        """음성 모드 메인 루프"""
        print("🎤 음성 모드로 시작합니다.")
        print("   인형을 터치하면 대화가 시작됩니다.")
        if not self.hardware._on_touch_callback:
            self.hardware.on_touch(self._on_touch)
        self.hardware.start_listening()

        # 세션 타임아웃 체크 스레드
        timeout_thread = threading.Thread(
            target=self._session_timeout_checker, daemon=True
        )
        timeout_thread.start()

        try:
            while self._running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self._end_session()

    def _on_touch(self):
        """터치 이벤트 핸들러"""
        if self._in_conversation:
            logger.info("이미 대화 중 — 터치 무시")
            return

        self._in_conversation = True
        self.hardware.led_on()

        # 인사
        greeting = self.engine.generate_proactive_greeting("morning")
        logger.info("인사: %s", greeting)
        if self.player and self.tts_engine:
            self.player.play_text(greeting, self.tts_engine)

        # 대화 루프
        threading.Thread(target=self._voice_conversation_loop, daemon=True).start()

    def _voice_conversation_loop(self):
        """음성 대화 루프 (별도 스레드)"""
        try:
            while self._in_conversation and self._running:
                # 녹음
                audio_bytes = self.recorder.record_until_silence()

                if audio_bytes is None:
                    # 세션 타임아웃 체크
                    if time.time() - self._last_activity > SESSION_TIMEOUT:
                        self._end_conversation_gracefully()
                        break
                    continue

                self._last_activity = time.time()

                # STT
                text = self.stt.transcribe_from_bytes(audio_bytes)
                if not text:
                    continue

                logger.info("할머니: %s", text)

                # 대화 생성
                response = self.engine.chat(text)
                logger.info("AI: %s", response)

                # TTS 재생
                if self.player and self.tts_engine:
                    self.player.play_text(response, self.tts_engine)

                # 긴급 알림
                self._check_and_notify(text)

        except Exception as e:
            logger.error("대화 루프 오류: %s", e)
        finally:
            self._in_conversation = False
            self.hardware.led_off()

    def _end_conversation_gracefully(self):
        """대화 자연스럽게 종료"""
        farewell = "할머니, 좋은 이야기 들려주셔서 고마워요~ 다음에 또 이야기해요!"
        logger.info("대화 종료: %s", farewell)

        if self.player and self.tts_engine:
            self.player.play_text(farewell, self.tts_engine)

        self._in_conversation = False
        self.hardware.led_off()
        self.hardware.led_blink(times=2)

        # 세션 요약
        self.engine.summarize_session()

    def _session_timeout_checker(self):
        """세션 타임아웃 체크 (별도 스레드)"""
        while self._running:
            if (
                self._in_conversation
                and time.time() - self._last_activity > SESSION_TIMEOUT
            ):
                logger.info("세션 타임아웃 (%d초)", SESSION_TIMEOUT)
                self._end_conversation_gracefully()
            time.sleep(5)

    # ─────────────────────────────────────────
    # 알림
    # ─────────────────────────────────────────
    def _check_and_notify(self, text: str):
        """긴급 키워드 체크 + 보호자 알림"""
        alerts = self.engine._check_emergency(text)
        for alert in alerts:
            self.notifier.send_emergency_alert(
                alert_type=alert["type"],
                keyword=alert["keyword"],
                context=alert["text"],
            )

    def _speak_if_enabled(self, text: str):
        """음성 출력 (--speak 옵션)"""
        if self.speak and self.player and self.tts_engine:
            try:
                self.player.play_text(text, self.tts_engine)
            except Exception as e:
                logger.debug("TTS 재생 실패: %s", e)

    # ─────────────────────────────────────────
    # 종료
    # ─────────────────────────────────────────
    def _end_session(self):
        """세션 종료 및 정리"""
        logger.info("세션 종료 중...")
        self._running = False
        self._in_conversation = False

        # 대화 요약 저장
        summary = self.engine.summarize_session()
        if summary:
            logger.info("세션 요약: %s", summary[:80])

        # 하드웨어 정리
        self.hardware.cleanup()
        if self.recorder:
            self.recorder.cleanup()

        print("\n🧸 할머니 말벗 에이전트를 종료합니다. 다음에 또 만나요!")

    def _signal_handler(self, signum, frame):
        """시그널 핸들러"""
        logger.info("종료 시그널 수신: %s", signum)
        self._end_session()
        sys.exit(0)


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="🧸 할머니 말벗 AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--text", action="store_true",
        help="텍스트 모드로 실행 (마이크/스피커 없이)"
    )
    parser.add_argument(
        "--speak", action="store_true",
        help="텍스트 모드에서도 음성 출력 활성화"
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="디버그 로깅 활성화"
    )

    args = parser.parse_args()

    # 로깅 설정
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # 에이전트 실행
    agent = GrandmotherAgent(text_mode=args.text, speak=args.speak)
    agent.run()


if __name__ == "__main__":
    main()
