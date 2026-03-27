#!/usr/bin/env python3
"""
🧸 for-grandmother — 웹 테스트 서버
스마트폰 브라우저에서 대화 테스트용

실행:
    python web.py
    → http://localhost:9002 (같은 Wi-Fi의 폰에서도 접속 가능)
"""
from __future__ import annotations

import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from src.memory import MemoryManager
from src.conversation import ConversationEngine

# 로깅
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("web")

# 초기화
logger.info("🧸 웹 테스트 서버 초기화...")
memory = MemoryManager()
memory.init_default_profile()
engine = ConversationEngine(memory)
logger.info("✅ 초기화 완료!")

app = FastAPI(title="🧸 할머니 말벗 에이전트 - 테스트")


# ─────────────────────────────────────────
# API 엔드포인트
# ─────────────────────────────────────────

@app.post("/api/chat")
async def chat(request: Request):
    """텍스트 대화 API"""
    body = await request.json()
    user_input = body.get("message", "").strip()

    if not user_input:
        return JSONResponse({"error": "메시지가 비어있습니다"}, status_code=400)

    logger.info("👵 할머니: %s", user_input)
    response_text = engine.chat(user_input)
    logger.info("🧸 AI: %s", response_text)

    # 긴급 키워드 체크
    alerts = engine._check_emergency(user_input)
    alert_types = [a["type"] for a in alerts] if alerts else []

    return JSONResponse({
        "response": response_text,
        "alerts": alert_types,
    })


@app.post("/api/greeting")
async def greeting(request: Request):
    """선제적 인사 생성 API"""
    body = await request.json()
    greeting_type = body.get("type", "morning")
    text = engine.generate_proactive_greeting(greeting_type)
    return JSONResponse({"response": text})


@app.get("/api/memory")
async def get_memory():
    """메모리 상태 확인 API"""
    short_term = memory.get_short_term()
    profile = memory.get_profile()
    summaries = memory.get_all_summaries()
    stats = memory.get_conversation_stats(days=30)

    return JSONResponse({
        "short_term_turns": len(short_term),
        "short_term": short_term[-6:],  # 최근 6턴만
        "profile": profile,
        "long_term_summaries": summaries[-5:],  # 최근 5개
        "stats": stats,
    })


@app.post("/api/end_session")
async def end_session():
    """세션 종료 + 요약 저장"""
    summary = engine.summarize_session()
    return JSONResponse({"summary": summary})


# ─────────────────────────────────────────
# 웹 UI
# ─────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_PAGE


HTML_PAGE = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>🧸 할머니 말벗 테스트</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: -apple-system, 'Apple SD Gothic Neo', sans-serif;
    background: #FFF8F0;
    color: #333;
    height: 100dvh;
    display: flex;
    flex-direction: column;
  }

  /* 헤더 */
  .header {
    background: #FF9E80;
    color: white;
    padding: 14px 20px;
    text-align: center;
    font-size: 18px;
    font-weight: 700;
    flex-shrink: 0;
  }
  .header small {
    font-size: 11px;
    font-weight: 400;
    opacity: 0.85;
    display: block;
    margin-top: 2px;
  }

  /* 채팅 영역 */
  .chat-area {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    -webkit-overflow-scrolling: touch;
  }

  .msg {
    max-width: 82%;
    padding: 12px 16px;
    border-radius: 18px;
    font-size: 16px;
    line-height: 1.5;
    word-break: keep-all;
    animation: fadeIn 0.25s ease;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .msg.user {
    align-self: flex-end;
    background: #FF9E80;
    color: white;
    border-bottom-right-radius: 4px;
  }

  .msg.ai {
    align-self: flex-start;
    background: white;
    color: #333;
    border-bottom-left-radius: 4px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }

  .msg.system {
    align-self: center;
    background: #FFF3E0;
    color: #E65100;
    font-size: 13px;
    padding: 8px 14px;
    border-radius: 12px;
  }

  .msg .alert-badge {
    display: inline-block;
    background: #FF5252;
    color: white;
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 10px;
    margin-top: 6px;
  }

  /* 타이핑 인디케이터 */
  .typing {
    align-self: flex-start;
    padding: 12px 20px;
    background: white;
    border-radius: 18px;
    border-bottom-left-radius: 4px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }
  .typing span {
    display: inline-block;
    width: 8px; height: 8px;
    background: #ccc;
    border-radius: 50%;
    margin: 0 2px;
    animation: bounce 1.2s infinite;
  }
  .typing span:nth-child(2) { animation-delay: 0.15s; }
  .typing span:nth-child(3) { animation-delay: 0.3s; }

  @keyframes bounce {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-6px); }
  }

  /* 입력 영역 */
  .input-area {
    flex-shrink: 0;
    padding: 12px 16px;
    padding-bottom: max(12px, env(safe-area-inset-bottom));
    background: white;
    border-top: 1px solid #eee;
    display: flex;
    gap: 10px;
    align-items: flex-end;
  }

  .input-area textarea {
    flex: 1;
    border: 2px solid #FFE0B2;
    border-radius: 20px;
    padding: 10px 16px;
    font-size: 16px;
    font-family: inherit;
    resize: none;
    max-height: 100px;
    outline: none;
    transition: border-color 0.2s;
  }
  .input-area textarea:focus {
    border-color: #FF9E80;
  }

  .btn {
    width: 44px; height: 44px;
    border: none;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    flex-shrink: 0;
    transition: transform 0.1s;
  }
  .btn:active { transform: scale(0.92); }

  .btn-send {
    background: #FF9E80;
    color: white;
  }
  .btn-send:disabled {
    background: #ddd;
  }

  .btn-mic {
    background: #FFF3E0;
    color: #FF6D00;
  }
  .btn-mic.recording {
    background: #FF5252;
    color: white;
    animation: pulse 1s infinite;
  }

  @keyframes pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(255,82,82,0.4); }
    50% { box-shadow: 0 0 0 10px rgba(255,82,82,0); }
  }

  /* 하단 툴바 */
  .toolbar {
    display: flex;
    gap: 8px;
    padding: 8px 16px;
    background: white;
    border-top: 1px solid #f0f0f0;
    flex-shrink: 0;
  }
  .toolbar button {
    flex: 1;
    padding: 8px;
    border: 1px solid #FFE0B2;
    border-radius: 12px;
    background: #FFF8F0;
    font-size: 12px;
    color: #666;
    cursor: pointer;
  }
  .toolbar button:active { background: #FFE0B2; }

  /* TTS 토글 */
  .tts-toggle {
    position: absolute;
    top: 12px;
    right: 16px;
    font-size: 12px;
    color: rgba(255,255,255,0.9);
    cursor: pointer;
    background: rgba(0,0,0,0.15);
    border: none;
    padding: 4px 10px;
    border-radius: 12px;
  }
</style>
</head>
<body>

<div class="header" style="position: relative;">
  🧸 할머니 말벗 테스트
  <small>윤수 테스트용 — 할머니처럼 말해보세요</small>
  <button class="tts-toggle" onclick="toggleTTS()" id="ttsBtn">🔇 음성 OFF</button>
</div>

<div class="chat-area" id="chatArea"></div>

<div class="input-area">
  <button class="btn btn-mic" id="micBtn" onclick="toggleMic()" title="음성 입력">🎤</button>
  <textarea id="input" rows="1" placeholder="할머니처럼 말해보세요..."
    oninput="autoResize(this)" onkeydown="handleKey(event)"></textarea>
  <button class="btn btn-send" id="sendBtn" onclick="sendMessage()" disabled>➤</button>
</div>

<div class="toolbar">
  <button onclick="getGreeting('morning')">🌅 아침 인사</button>
  <button onclick="getGreeting('afternoon')">☀️ 오후 인사</button>
  <button onclick="viewMemory()">🧠 메모리</button>
  <button onclick="endSession()">📝 세션 종료</button>
</div>

<script>
const chatArea = document.getElementById('chatArea');
const input = document.getElementById('input');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
let ttsEnabled = false;
let recognition = null;
let isRecording = false;

// ── 메시지 전송 ──
async function sendMessage() {
  const text = input.value.trim();
  if (!text) return;

  addMsg(text, 'user');
  input.value = '';
  input.style.height = 'auto';
  sendBtn.disabled = true;
  showTyping();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text }),
    });
    const data = await res.json();
    hideTyping();
    addMsg(data.response, 'ai', data.alerts);
    if (ttsEnabled) speak(data.response);
  } catch (e) {
    hideTyping();
    addMsg('⚠️ 서버 연결 오류', 'system');
  }
}

// ── 메시지 표시 ──
function addMsg(text, type, alerts = []) {
  const div = document.createElement('div');
  div.className = `msg ${type}`;
  div.textContent = text;

  if (alerts.length > 0) {
    alerts.forEach(a => {
      const badge = document.createElement('div');
      badge.className = 'alert-badge';
      badge.textContent = a === 'emergency' ? '🚨 건강 키워드 감지' : '💛 감정 키워드 감지';
      div.appendChild(badge);
    });
  }

  chatArea.appendChild(div);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function showTyping() {
  const div = document.createElement('div');
  div.className = 'typing';
  div.id = 'typingIndicator';
  div.innerHTML = '<span></span><span></span><span></span>';
  chatArea.appendChild(div);
  chatArea.scrollTop = chatArea.scrollHeight;
}

function hideTyping() {
  const el = document.getElementById('typingIndicator');
  if (el) el.remove();
}

// ── 음성 입력 (Web Speech API) ──
function toggleMic() {
  if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
    addMsg('⚠️ 이 브라우저는 음성 인식을 지원하지 않아요', 'system');
    return;
  }

  if (isRecording) {
    recognition.stop();
    return;
  }

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = 'ko-KR';
  recognition.continuous = false;
  recognition.interimResults = true;

  recognition.onstart = () => {
    isRecording = true;
    micBtn.classList.add('recording');
    micBtn.textContent = '⏹';
    input.placeholder = '듣고 있어요...';
  };

  recognition.onresult = (e) => {
    const transcript = Array.from(e.results)
      .map(r => r[0].transcript)
      .join('');
    input.value = transcript;
    sendBtn.disabled = !transcript.trim();
  };

  recognition.onend = () => {
    isRecording = false;
    micBtn.classList.remove('recording');
    micBtn.textContent = '🎤';
    input.placeholder = '할머니처럼 말해보세요...';
    // 자동 전송
    if (input.value.trim()) sendMessage();
  };

  recognition.onerror = (e) => {
    isRecording = false;
    micBtn.classList.remove('recording');
    micBtn.textContent = '🎤';
    if (e.error !== 'no-speech') {
      addMsg(`⚠️ 음성 인식 오류: ${e.error}`, 'system');
    }
  };

  recognition.start();
}

// ── TTS (브라우저 내장) ──
function toggleTTS() {
  ttsEnabled = !ttsEnabled;
  document.getElementById('ttsBtn').textContent = ttsEnabled ? '🔊 음성 ON' : '🔇 음성 OFF';
}

function speak(text) {
  if (!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = 'ko-KR';
  utter.rate = 0.85;
  utter.pitch = 1.0;
  // 한국어 음성 선택
  const voices = window.speechSynthesis.getVoices();
  const koVoice = voices.find(v => v.lang.startsWith('ko'));
  if (koVoice) utter.voice = koVoice;
  window.speechSynthesis.speak(utter);
}
// 음성 목록 미리 로드
if ('speechSynthesis' in window) {
  speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
}

// ── 선제적 인사 ──
async function getGreeting(type) {
  showTyping();
  try {
    const res = await fetch('/api/greeting', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type }),
    });
    const data = await res.json();
    hideTyping();
    addMsg(data.response, 'ai');
    if (ttsEnabled) speak(data.response);
  } catch (e) {
    hideTyping();
    addMsg('⚠️ 서버 연결 오류', 'system');
  }
}

// ── 메모리 확인 ──
async function viewMemory() {
  try {
    const res = await fetch('/api/memory');
    const data = await res.json();
    let text = `🧠 메모리 상태\\n`;
    text += `단기 메모리: ${data.short_term_turns}턴\\n`;
    text += `장기 요약: ${data.long_term_summaries.length}개\\n`;
    text += `총 세션: ${data.stats.total_sessions}회`;
    if (data.stats.last_chat) text += `\\n마지막 대화: ${data.stats.last_chat}`;
    addMsg(text, 'system');
  } catch (e) {
    addMsg('⚠️ 서버 연결 오류', 'system');
  }
}

// ── 세션 종료 ──
async function endSession() {
  try {
    const res = await fetch('/api/end_session', { method: 'POST' });
    const data = await res.json();
    const text = data.summary ? `📝 세션 요약 저장됨:\\n${data.summary}` : '📝 저장할 대화가 없어요';
    addMsg(text, 'system');
  } catch (e) {
    addMsg('⚠️ 서버 연결 오류', 'system');
  }
}

// ── 유틸 ──
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 100) + 'px';
  sendBtn.disabled = !el.value.trim();
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

// 초기 인사
window.addEventListener('load', () => getGreeting('morning'));
</script>

</body>
</html>
"""


# ─────────────────────────────────────────
# 서버 실행
# ─────────────────────────────────────────

if __name__ == "__main__":
    import socket

    # 로컬 IP 확인
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = "확인불가"

    print()
    print("=" * 50)
    print("  🧸 할머니 말벗 에이전트 — 웹 테스트 서버")
    print("=" * 50)
    print()
    print(f"  💻 PC에서:     http://localhost:9002")
    print(f"  📱 폰에서:     http://{local_ip}:9002")
    print(f"                 (같은 Wi-Fi 필요)")
    print()
    print("  Ctrl+C 로 종료")
    print("=" * 50)
    print()

    uvicorn.run(app, host="0.0.0.0", port=9002, log_level="info")
