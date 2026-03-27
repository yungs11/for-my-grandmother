#!/usr/bin/env python3
"""
🧸 for-grandmother 통합 테스트
텍스트 모드로 대화 엔진 + 메모리 + 긴급 키워드 감지 테스트
"""

import sys
import os
import tempfile
from pathlib import Path

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# OpenRouter 키 설정
os.environ["OPENROUTER_API_KEY"] = "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"
os.environ["LLM_PROVIDER"] = "openrouter"

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s", datefmt="%H:%M:%S")

from src.memory import MemoryManager
from src.conversation import ConversationEngine


def main():
    print()
    print("=" * 55)
    print("  🧸 할머니 말벗 에이전트 — 통합 테스트")
    print("=" * 55)
    print()

    # 1. 메모리 초기화 (임시 DB 파일)
    print("📦 메모리 시스템 초기화...")
    tmp_db = Path(tempfile.mktemp(suffix=".db"))
    memory = MemoryManager(db_path=tmp_db)
    memory.init_default_profile()
    print("  ✅ 메모리 초기화 완료")
    print()

    # 2. 대화 엔진 초기화
    print("🤖 대화 엔진 초기화 (OpenRouter)...")
    engine = ConversationEngine(memory)
    print("  ✅ 대화 엔진 준비 완료")
    print()

    # 3. 선제적 인사 테스트
    print("─" * 55)
    print("🌅 [테스트 1] 선제적 아침 인사 생성")
    print("─" * 55)
    greeting = engine.generate_proactive_greeting("morning", weather="맑음, 15도")
    print(f"  🧸: {greeting}")
    print()

    # 4. 대화 테스트
    test_inputs = [
        "오늘 날씨가 좋구만. 강릉 바다가 생각나네.",
        "그때 할아버지랑 같이 바다에 많이 갔어. 참 좋았는데...",
        "요즘은 혼자라 외롭기도 하고... 승혜가 요즘 바쁜가봐.",
    ]

    print("─" * 55)
    print("💬 [테스트 2] 멀티턴 대화 (3턴)")
    print("─" * 55)
    for i, user_input in enumerate(test_inputs, 1):
        print(f"\n  [턴 {i}]")
        print(f"  👵 할머니: {user_input}")
        response = engine.chat(user_input)
        print(f"  🧸 AI:     {response}")
    print()

    # 5. 긴급 키워드 감지 테스트
    print("─" * 55)
    print("🚨 [테스트 3] 긴급 키워드 감지")
    print("─" * 55)
    emergency_test = "아이고 머리가 아파서 약을 못 찾겠어"
    alerts = engine._check_emergency(emergency_test)
    print(f"  입력: \"{emergency_test}\"")
    print(f"  감지된 키워드: {[a['keyword'] for a in alerts]}")
    print(f"  알림 타입: {[a['type'] for a in alerts]}")
    print()

    # 6. 감정 분석 테스트
    print("─" * 55)
    print("💛 [테스트 4] 감정 분석")
    print("─" * 55)
    mood_tests = [
        ("오늘 맛있는 거 먹어서 기분이 좋아", "긍정"),
        ("할아버지가 보고 싶어서 슬프다", "부정"),
        ("오늘 날씨가 흐리구나", "중립"),
    ]
    for text, expected in mood_tests:
        mood = engine._detect_mood(text)
        status = "✅" if mood == expected else "❌"
        print(f"  {status} \"{text}\" → {mood} (기대: {expected})")
    print()

    # 7. 메모리 확인
    print("─" * 55)
    print("🧠 [테스트 5] 단기 메모리 상태")
    print("─" * 55)
    short_term = memory.get_short_term()
    print(f"  저장된 턴 수: {len(short_term)}")
    for turn in short_term:
        role = "👵" if turn["role"] == "user" else "🧸"
        content = turn["content"][:50] + ("..." if len(turn["content"]) > 50 else "")
        print(f"    {role} {content}")
    print()

    # 8. 세션 요약 테스트
    print("─" * 55)
    print("📝 [테스트 6] 세션 요약 (장기 메모리 저장)")
    print("─" * 55)
    summary = engine.summarize_session()
    print(f"  요약: {summary}")
    print()

    # 정리
    tmp_db.unlink(missing_ok=True)

    print("=" * 55)
    print("  ✅ 모든 테스트 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
