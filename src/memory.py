"""
할머니 말벗 AI Agent - 3계층 메모리 시스템
단기 메모리 / 장기 메모리 / 프로필 메모리
"""

from __future__ import annotations

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from config.settings import (
    DB_PATH,
    SHORT_TERM_MAX_TURNS,
    LONG_TERM_SUMMARY_DAYS,
)

logger = logging.getLogger(__name__)


class MemoryManager:
    """3계층 메모리를 관리하는 클래스"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()
        self._short_term: list[dict] = []  # 현재 세션 대화

    # ─────────────────────────────────────────
    # DB 초기화
    # ─────────────────────────────────────────
    def _init_db(self):
        """SQLite 데이터베이스 및 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS long_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    date TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    mood TEXT,
                    keywords TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS profile_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_conv_session
                    ON conversations(session_id);
                CREATE INDEX IF NOT EXISTS idx_conv_timestamp
                    ON conversations(timestamp);
                CREATE INDEX IF NOT EXISTS idx_ltm_date
                    ON long_term_memory(date);
            """)
            logger.info("메모리 DB 초기화 완료: %s", self.db_path)

    # ─────────────────────────────────────────
    # 단기 메모리 (Short-term)
    # ─────────────────────────────────────────
    def add_turn(self, role: str, content: str, session_id: str):
        """대화 턴 추가 (단기 메모리 + DB 저장)"""
        turn = {"role": role, "content": content}
        self._short_term.append(turn)

        # 최대 턴 수 초과 시 오래된 것부터 제거
        if len(self._short_term) > SHORT_TERM_MAX_TURNS:
            self._short_term = self._short_term[-SHORT_TERM_MAX_TURNS:]

        # DB에도 저장 (영구 보관)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
                (session_id, role, content),
            )

    def get_short_term(self) -> list[dict]:
        """현재 세션의 단기 메모리 반환"""
        return list(self._short_term)

    def clear_short_term(self):
        """단기 메모리 초기화 (세션 종료 시)"""
        self._short_term.clear()

    def get_session_conversation(self, session_id: str) -> list[dict]:
        """특정 세션의 전체 대화 내용 반환"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY timestamp",
                (session_id,),
            ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]

    # ─────────────────────────────────────────
    # 장기 메모리 (Long-term)
    # ─────────────────────────────────────────
    def save_long_term_summary(
        self,
        session_id: str,
        date: str,
        summary: str,
        mood: str = "",
        keywords: str = "",
    ):
        """장기 메모리에 대화 요약 저장"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO long_term_memory
                   (session_id, date, summary, mood, keywords)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, date, summary, mood, keywords),
            )
        logger.info("장기 메모리 저장: %s", date)

    def get_recent_summaries(self, days: int = LONG_TERM_SUMMARY_DAYS) -> str:
        """최근 N일간의 대화 요약 반환"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT date, summary, mood
                   FROM long_term_memory
                   WHERE date >= ?
                   ORDER BY date DESC""",
                (cutoff,),
            ).fetchall()

        if not rows:
            return ""

        parts = []
        for date, summary, mood in rows:
            entry = f"[{date}] {summary}"
            if mood:
                entry += f" (감정: {mood})"
            parts.append(entry)

        return "\n".join(parts)

    def get_all_summaries(self) -> list[dict]:
        """모든 장기 메모리 요약 반환"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                """SELECT date, summary, mood, keywords
                   FROM long_term_memory
                   ORDER BY date DESC""",
            ).fetchall()
        return [
            {"date": r[0], "summary": r[1], "mood": r[2], "keywords": r[3]}
            for r in rows
        ]

    # ─────────────────────────────────────────
    # 프로필 메모리 (Persistent)
    # ─────────────────────────────────────────
    def get_profile(self) -> dict:
        """프로필 메모리 전체 반환"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT key, value FROM profile_memory"
            ).fetchall()

        profile = {}
        for key, value in rows:
            try:
                profile[key] = json.loads(value)
            except json.JSONDecodeError:
                profile[key] = value
        return profile

    def update_profile(self, key: str, value):
        """프로필 메모리 특정 키 업데이트"""
        value_str = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO profile_memory (key, value, updated_at)
                   VALUES (?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(key) DO UPDATE SET
                       value = excluded.value,
                       updated_at = CURRENT_TIMESTAMP""",
                (key, value_str),
            )
        logger.info("프로필 메모리 업데이트: %s", key)

    def init_default_profile(self):
        """기본 프로필 메모리 초기화 (최초 실행 시)"""
        default_profile = {
            "frequently_mentioned": {
                "people": ["할아버지", "어머니", "영혜", "승혜", "승현", "승희"],
                "places": ["강릉", "초등학교", "바닷가"],
                "topics": ["교사 시절", "할아버지 추억", "어머니 추억"],
            },
            "emotional_state": {
                "recent_mood": "",
                "triggers_positive": ["손주 이야기", "강릉 바다", "교사 시절 보람"],
                "triggers_negative": ["할아버지 병간호", "외로움"],
            },
            "preferences": {
                "conversation_time": "오전 10시, 오후 3시",
                "favorite_topics": ["옛날이야기", "날씨", "가족"],
            },
        }

        existing = self.get_profile()
        if not existing:
            for key, value in default_profile.items():
                self.update_profile(key, value)
            logger.info("기본 프로필 메모리 초기화 완료")

    # ─────────────────────────────────────────
    # 통계
    # ─────────────────────────────────────────
    def get_conversation_stats(self, days: int = 7) -> dict:
        """최근 N일간 대화 통계"""
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            # 총 대화 수
            total = conn.execute(
                """SELECT COUNT(DISTINCT session_id)
                   FROM conversations
                   WHERE timestamp >= ?""",
                (cutoff,),
            ).fetchone()[0]

            # 최근 대화 날짜
            last_chat = conn.execute(
                "SELECT MAX(timestamp) FROM conversations"
            ).fetchone()[0]

            # 감정 분포
            moods = conn.execute(
                """SELECT mood, COUNT(*)
                   FROM long_term_memory
                   WHERE date >= ?
                   GROUP BY mood""",
                (cutoff,),
            ).fetchall()

        return {
            "total_sessions": total,
            "last_chat": last_chat,
            "mood_distribution": {m[0]: m[1] for m in moods if m[0]},
            "period_days": days,
        }

    def get_last_chat_date(self) -> str | None:
        """마지막 대화 날짜 반환"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT MAX(timestamp) FROM conversations"
            ).fetchone()
        return row[0] if row and row[0] else None

    def days_since_last_chat(self) -> int | None:
        """마지막 대화 이후 경과 일수"""
        last = self.get_last_chat_date()
        if not last:
            return None
        last_dt = datetime.fromisoformat(last)
        return (datetime.now() - last_dt).days
