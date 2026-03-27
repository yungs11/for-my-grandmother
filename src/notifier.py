"""
할머니 말벗 AI Agent - 보호자 알림 시스템
텔레그램 봇을 통한 일일 리포트 + 긴급 알림
"""

import logging
from datetime import datetime

from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """텔레그램 봇을 통한 보호자 알림"""

    def __init__(self):
        self.token = TELEGRAM_BOT_TOKEN
        self.chat_id = TELEGRAM_CHAT_ID
        self._enabled = bool(self.token and self.chat_id)

        if not self._enabled:
            logger.warning("텔레그램 알림 비활성화 (토큰/채팅ID 미설정)")

    @property
    def api_url(self) -> str:
        return f"https://api.telegram.org/bot{self.token}"

    def send_message(self, text: str) -> bool:
        """텔레그램 메시지 전송"""
        if not self._enabled:
            logger.info("[알림 미전송] %s", text[:50])
            return False

        try:
            import requests
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
            if response.ok:
                logger.info("텔레그램 알림 전송 성공")
                return True
            else:
                logger.error("텔레그램 전송 실패: %s", response.text)
                return False
        except Exception as e:
            logger.error("텔레그램 전송 오류: %s", e)
            return False

    # ─────────────────────────────────────────
    # 긴급 알림
    # ─────────────────────────────────────────
    def send_emergency_alert(self, alert_type: str, keyword: str, context: str):
        """긴급 알림 전송"""
        emoji = "🚨" if alert_type == "emergency" else "💛"
        now = datetime.now().strftime("%H:%M")

        message = (
            f"{emoji} *할머니 긴급 알림* {emoji}\n\n"
            f"⏰ 시간: {now}\n"
            f"🔑 감지 키워드: {keyword}\n"
            f"💬 발화 내용: {context[:100]}\n\n"
            f"할머니 상태를 확인해주세요."
        )
        return self.send_message(message)

    # ─────────────────────────────────────────
    # 일일 리포트
    # ─────────────────────────────────────────
    def send_daily_report(
        self,
        date: str,
        session_count: int,
        total_turns: int,
        summary: str,
        mood: str,
    ):
        """일일 대화 리포트 전송"""
        mood_emoji = {"긍정": "😊", "부정": "😢", "중립": "😐"}.get(mood, "😐")

        message = (
            f"📋 *할머니 일일 리포트* — {date}\n\n"
            f"💬 대화 횟수: {session_count}회\n"
            f"🔄 총 대화 턴: {total_turns}턴\n"
            f"{mood_emoji} 감정 상태: {mood}\n\n"
            f"📝 *대화 요약*\n{summary}\n\n"
            f"할머니의 오늘 하루였습니다 💕"
        )
        return self.send_message(message)

    # ─────────────────────────────────────────
    # 장시간 무응답 알림
    # ─────────────────────────────────────────
    def send_no_response_alert(self, hours_since: float):
        """장시간 무응답 알림"""
        message = (
            f"⚠️ *할머니 무응답 알림*\n\n"
            f"예정된 대화 시간에 {hours_since:.0f}시간째 응답이 없습니다.\n"
            f"할머니 상태를 확인해주세요."
        )
        return self.send_message(message)
