"""
for-grandmother 프로젝트 설정
할머니 말벗 AI Agent 설정 파일
"""

import os
from pathlib import Path

# .env 파일 자동 로드
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# ─────────────────────────────────────────────
# 프로젝트 경로
# ─────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────
# API 키 (환경변수에서 로드)
# ─────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GOOGLE_TTS_API_KEY = os.getenv("GOOGLE_TTS_API_KEY", "")
CLOVA_CLIENT_ID = os.getenv("CLOVA_CLIENT_ID", "")
CLOVA_CLIENT_SECRET = os.getenv("CLOVA_CLIENT_SECRET", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ─────────────────────────────────────────────
# LLM API 설정
# ─────────────────────────────────────────────
# API 제공자: "anthropic" 또는 "openrouter"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "openai/gpt-4.1-mini")  # OpenRouter 모델명
CLAUDE_MAX_TOKENS = 300  # 할머니에게 짧게 답변
CLAUDE_TEMPERATURE = 0.7  # 자연스러운 대화

# ─────────────────────────────────────────────
# STT 설정 (Whisper)
# ─────────────────────────────────────────────
WHISPER_MODEL = "base"  # tiny, base, small, medium, large
WHISPER_LANGUAGE = "ko"
WHISPER_DEVICE = "cpu"  # 라즈베리파이에서는 cpu

# ─────────────────────────────────────────────
# TTS 설정
# ─────────────────────────────────────────────
TTS_PROVIDER = "google"  # "google", "clova", "elevenlabs"
TTS_LANGUAGE = "ko"
TTS_VOICE_NAME = "ko-KR-Wavenet-A"  # Google: 따뜻한 여성 음성
TTS_SPEAKING_RATE = 0.85  # 약간 느리게 (0.25 ~ 4.0)
TTS_PITCH = -1.0  # 살짝 낮은 톤 (-20.0 ~ 20.0)

# ─────────────────────────────────────────────
# 오디오 설정
# ─────────────────────────────────────────────
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
AUDIO_CHUNK_SIZE = 1024
SILENCE_THRESHOLD = 500  # 침묵 감지 임계값 (조절 필요)
SILENCE_DURATION = 2.0  # 초 (발화 종료 판정)
SESSION_TIMEOUT = 180.0  # 3분 무응답 시 세션 종료

# ─────────────────────────────────────────────
# GPIO 핀 설정 (라즈베리파이)
# ─────────────────────────────────────────────
TOUCH_SENSOR_PIN = 17  # BCM 핀 번호
LED_PIN = 27  # 상태 표시 LED (선택)
DEBOUNCE_TIME = 0.3  # 터치 디바운스 (초)

# ─────────────────────────────────────────────
# 메모리 설정
# ─────────────────────────────────────────────
SHORT_TERM_MAX_TURNS = 15  # 단기 메모리 최대 턴 수
LONG_TERM_SUMMARY_DAYS = 30  # 최근 N일 요약 포함
DB_PATH = DATA_DIR / "grandmother.db"

# ─────────────────────────────────────────────
# 선제적 대화 스케줄
# ─────────────────────────────────────────────
PROACTIVE_SCHEDULE = [
    {"hour": 10, "minute": 0, "type": "morning"},
    {"hour": 15, "minute": 0, "type": "afternoon"},
]
PROACTIVE_NO_CHAT_THRESHOLD_DAYS = 3  # N일 대화 없으면 빈도 증가

# ─────────────────────────────────────────────
# 보호자 알림 설정
# ─────────────────────────────────────────────
EMERGENCY_KEYWORDS = [
    "아프다", "아파", "넘어졌", "넘어져", "어지럽", "어지러",
    "숨이 차", "가슴이 아", "머리가 아", "다쳤", "피가 나",
    "약을 못", "약이 없", "못 일어나", "도와줘",
]
DEPRESSION_KEYWORDS = [
    "죽고 싶", "살기 싫", "외롭", "혼자", "쓸모없",
    "나가기 싫", "아무도 없", "보고 싶", "그리워",
]
