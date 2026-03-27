"""
할머니 말벗 AI Agent - 대화 엔진
LLM API를 통한 대화 생성 + 긴급 키워드 감지 + 대화 요약
Anthropic 직접 호출 / OpenRouter 호환 지원
"""
from __future__ import annotations

import logging
from datetime import datetime

from config.settings import (
    ANTHROPIC_API_KEY,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    LLM_PROVIDER,
    CLAUDE_MODEL,
    CLAUDE_MAX_TOKENS,
    CLAUDE_TEMPERATURE,
    EMERGENCY_KEYWORDS,
    DEPRESSION_KEYWORDS,
)
from src.prompts import (
    SYSTEM_PROMPT,
    SUMMARY_PROMPT,
    build_conversation_prompt,
)
from src.memory import MemoryManager

logger = logging.getLogger(__name__)


def _create_llm_client():
    """LLM 클라이언트 생성 (provider에 따라 분기)"""
    if LLM_PROVIDER == "openrouter":
        # requests 기반 클라이언트 (프록시 호환)
        return {"type": "openrouter", "api_key": OPENROUTER_API_KEY}
    else:
        import anthropic
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def _call_llm(client, model: str, system: str, messages: list[dict],
              max_tokens: int = 300, temperature: float = 0.7) -> str:
    """LLM 호출 (provider에 따라 분기)"""
    if LLM_PROVIDER == "openrouter":
        import requests
        # requests 직접 호출 (프록시 자동 지원)
        full_messages = [{"role": "system", "content": system}] + messages
        response = requests.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {client['api_key']}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": full_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=30,
        )
        if not response.ok:
            logger.error("OpenRouter 응답 상세: %s", response.text)
            response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    else:
        # Anthropic 직접 호출
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
        return response.content[0].text.strip()


class ConversationEngine:
    """LLM 기반 대화 엔진"""

    def __init__(self, memory: MemoryManager):
        self.memory = memory
        self.client = _create_llm_client()
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info("대화 엔진 초기화 (provider: %s, model: %s)", LLM_PROVIDER, CLAUDE_MODEL)

    # ─────────────────────────────────────────
    # 메인 대화
    # ─────────────────────────────────────────
    def chat(self, user_input: str) -> str:
        """
        할머니 발화에 대한 응답 생성

        Args:
            user_input: 할머니가 말씀하신 내용 (STT 결과)

        Returns:
            AI 응답 텍스트
        """
        # 1. 긴급 키워드 체크
        alerts = self._check_emergency(user_input)
        if alerts:
            logger.warning("긴급 키워드 감지: %s", alerts)

        # 2. 단기 메모리에 사용자 발화 추가
        self.memory.add_turn("user", user_input, self.session_id)

        # 3. 메모리 컨텍스트 구성
        short_term = self.memory.get_short_term()
        long_term_summary = self.memory.get_recent_summaries()
        profile = self.memory.get_profile()

        # 4. 프롬프트 구성
        messages = build_conversation_prompt(
            short_term_memory=short_term[:-1],
            long_term_summary=long_term_summary,
            profile_memory=profile,
            current_input=user_input,
        )

        # 5. LLM 호출
        try:
            assistant_text = _call_llm(
                self.client, CLAUDE_MODEL, SYSTEM_PROMPT, messages,
                max_tokens=CLAUDE_MAX_TOKENS, temperature=CLAUDE_TEMPERATURE,
            )
        except Exception as e:
            logger.error("LLM API 오류: %s", e)
            assistant_text = "할머니, 잠깐만요~ 다시 한 번 말씀해주시겠어요?"

        # 6. 단기 메모리에 응답 추가
        self.memory.add_turn("assistant", assistant_text, self.session_id)

        logger.info("대화 턴 완료 — 입력: %s / 응답: %s", user_input[:30], assistant_text[:30])
        return assistant_text

    # ─────────────────────────────────────────
    # 대화 요약 (세션 종료 시)
    # ─────────────────────────────────────────
    def summarize_session(self) -> str:
        """현재 세션 대화를 요약하고 장기 메모리에 저장"""
        conversation = self.memory.get_session_conversation(self.session_id)
        if not conversation or len(conversation) < 2:
            return ""

        conv_text = "\n".join(
            f"{'할머니' if t['role'] == 'user' else 'AI'}: {t['content']}"
            for t in conversation
        )

        today = datetime.now().strftime("%Y-%m-%d")
        prompt = SUMMARY_PROMPT.format(conversation=conv_text, date=today)

        try:
            summary = _call_llm(
                self.client, CLAUDE_MODEL,
                "당신은 대화 요약 전문가입니다. 한국어로 간결하게 요약해주세요.",
                [{"role": "user", "content": prompt}],
                max_tokens=500, temperature=0.3,
            )
        except Exception as e:
            logger.error("요약 생성 오류: %s", e)
            summary = f"[{today}] 할머니와 대화 (자동 요약 실패)"

        # 장기 메모리에 저장
        mood = self._detect_mood(conv_text)
        keywords = self._extract_keywords(conv_text)
        self.memory.save_long_term_summary(
            session_id=self.session_id,
            date=today,
            summary=summary,
            mood=mood,
            keywords=keywords,
        )

        self.memory.clear_short_term()
        logger.info("세션 요약 완료: %s", summary[:50])
        return summary

    # ─────────────────────────────────────────
    # 선제적 대화 생성
    # ─────────────────────────────────────────
    def generate_proactive_greeting(
        self,
        greeting_type: str = "morning",
        weather: str = "",
        special_day: str = "",
    ) -> str:
        """선제적 인사말 생성"""
        recent_summary = self.memory.get_recent_summaries(days=3)

        if greeting_type == "morning":
            prompt = f"""
할머니에게 아침 인사를 해주세요.
오늘 날씨: {weather or '정보 없음'}
최근 대화: {recent_summary or '최근 대화 없음'}
특별한 날: {special_day or '없음'}

2~3문장으로 따뜻하게 아침 인사를 건네주세요.
"""
        else:
            prompt = f"""
할머니에게 오후 안부를 물어봐주세요.
오늘 날씨: {weather or '정보 없음'}
최근 대화: {recent_summary or '최근 대화 없음'}

2~3문장으로 자연스럽게 안부를 물어봐주세요.
"""

        try:
            return _call_llm(
                self.client, CLAUDE_MODEL, SYSTEM_PROMPT,
                [{"role": "user", "content": prompt}],
                max_tokens=200, temperature=0.8,
            )
        except Exception as e:
            logger.error("선제적 인사 생성 오류: %s", e)
            if greeting_type == "morning":
                return "할머니~ 좋은 아침이에요! 오늘도 건강하게 보내세요~"
            return "할머니~ 점심은 맛있게 드셨어요? 오후도 편안하게 보내세요~"

    # ─────────────────────────────────────────
    # 긴급 키워드 감지
    # ─────────────────────────────────────────
    def _check_emergency(self, text: str) -> list[dict]:
        """긴급 키워드 감지"""
        alerts = []
        for kw in EMERGENCY_KEYWORDS:
            if kw in text:
                alerts.append({"type": "emergency", "keyword": kw, "text": text})
        for kw in DEPRESSION_KEYWORDS:
            if kw in text:
                alerts.append({"type": "depression", "keyword": kw, "text": text})
        return alerts

    # ─────────────────────────────────────────
    # 감정 분석 (간단)
    # ─────────────────────────────────────────
    @staticmethod
    def _detect_mood(text: str) -> str:
        """대화 내용에서 간단한 감정 분석"""
        positive_words = ["좋", "행복", "기쁘", "재미", "맛있", "예쁘", "고맙", "감사"]
        negative_words = ["슬프", "아프", "외롭", "힘들", "보고 싶", "그리워", "걱정"]
        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)
        if pos_count > neg_count:
            return "긍정"
        elif neg_count > pos_count:
            return "부정"
        return "중립"

    @staticmethod
    def _extract_keywords(text: str) -> str:
        """대화 내용에서 주요 키워드 추출"""
        known_keywords = [
            "강릉", "바다", "학교", "교사", "할아버지", "어머니",
            "영혜", "승혜", "승현", "승희", "손주", "벚꽃",
        ]
        found = [kw for kw in known_keywords if kw in text]
        return ", ".join(found) if found else ""
