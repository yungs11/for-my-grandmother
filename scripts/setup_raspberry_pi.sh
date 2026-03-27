#!/bin/bash
# ─────────────────────────────────────────────
# 🧸 for-grandmother — 라즈베리파이 초기 셋업
# Raspberry Pi OS에서 실행
# ─────────────────────────────────────────────

set -e

echo "🧸 할머니 말벗 에이전트 — 라즈베리파이 셋업"
echo "============================================"

# 1. 시스템 업데이트
echo "📦 시스템 업데이트..."
sudo apt-get update && sudo apt-get upgrade -y

# 2. 오디오 관련 패키지
echo "🔊 오디오 패키지 설치..."
sudo apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    alsa-utils \
    pulseaudio \
    ffmpeg

# 3. Python 의존성
echo "🐍 Python 패키지 설치..."
pip3 install --break-system-packages -r requirements.txt

# 4. Whisper 추가 의존성
echo "🎙️ Whisper 의존성 설치..."
sudo apt-get install -y \
    libopenblas-dev \
    libblas-dev

# 5. GPIO 권한
echo "⚡ GPIO 권한 설정..."
sudo usermod -aG gpio $USER

# 6. 오디오 테스트
echo "🔊 오디오 출력 테스트..."
speaker-test -t wav -c 1 -l 1 2>/dev/null || echo "⚠️ 스피커 테스트 실패 — ALSA 설정을 확인하세요"

# 7. 마이크 테스트
echo "🎤 마이크 목록:"
arecord -l 2>/dev/null || echo "⚠️ 마이크를 찾을 수 없습니다"

# 8. .env 파일 생성
if [ ! -f .env ]; then
    echo "📝 .env 파일 생성..."
    cp .env.example .env
    echo "⚠️ .env 파일에 API 키를 설정해주세요!"
fi

echo ""
echo "✅ 셋업 완료!"
echo ""
echo "다음 단계:"
echo "  1. .env 파일에 ANTHROPIC_API_KEY 설정"
echo "  2. 텍스트 모드 테스트: python3 main.py --text"
echo "  3. 음성 모드 테스트: python3 main.py"
