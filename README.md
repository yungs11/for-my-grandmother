# 🧸 for-grandmother

외로우신 할머니를 위한 말벗 AI Agent

복실복실한 인형 속에 라즈베리파이가 들어있고, 인형을 터치하면 따뜻한 대화가 시작됩니다.

## 기능

- **음성 대화**: 마이크로 듣고, 스피커로 대답 (Whisper STT + Google/CLOVA TTS)
- **대화 기억**: 3계층 메모리 시스템 (단기 / 장기 요약 / 프로필)
- **먼저 말 걸기**: 아침, 오후에 할머니에게 먼저 인사
- **보호자 알림**: 긴급 키워드 감지 시 텔레그램으로 즉시 알림
- **일일 리포트**: 매일 대화 요약 + 감정 상태 리포트

## 빠른 시작

### 1. 환경 설정
```bash
cp .env.example .env
# .env 파일에 ANTHROPIC_API_KEY 입력
```

### 2. 텍스트 모드 (개발/테스트)
```bash
pip install anthropic python-dotenv
python main.py --text
```

### 3. 라즈베리파이 셋업
```bash
chmod +x scripts/setup_raspberry_pi.sh
./scripts/setup_raspberry_pi.sh
python main.py
```

## 프로젝트 구조

```text
for-grandmother/
├── main.py              # 메인 애플리케이션
├── config/
│   └── settings.py      # 전체 설정
├── src/
│   ├── prompts.py       # 시스템 프롬프트 & 대화 구성
│   ├── memory.py        # 3계층 메모리 시스템
│   ├── audio.py         # STT + TTS + 녹음/재생
│   ├── conversation.py  # Claude API 대화 엔진
│   ├── hardware.py      # GPIO 터치 센서 + LED
│   └── notifier.py      # 텔레그램 보호자 알림
├── scripts/
│   └── setup_raspberry_pi.sh
├── data/                # DB, 로그 (자동 생성)
├── requirements.txt
└── .env.example
```

## 하드웨어 구성 (라즈베리파이)

| 부품 | 연결 |
|------|------|
| 압력/터치 센서 | GPIO 17 (BCM) |
| 상태 LED | GPIO 27 (BCM) |
| USB 마이크 | USB 포트 |
| 스피커 | 3.5mm 오디오 잭 |

## 실행 옵션

```bash
python main.py              # 음성 모드 (기본)
python main.py --text       # 텍스트 모드
python main.py --text --speak  # 텍스트 입력 + 음성 출력
python main.py --debug      # 디버그 로그
```
