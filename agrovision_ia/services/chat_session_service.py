import threading
from services.logging_config import get_logger

log = get_logger("agrovision.chat_session")
DEFAULT_MAX_MESSAGES = 16


class ChatSessionService:
    def __init__(self, max_messages: int = DEFAULT_MAX_MESSAGES):
        self._sessions: dict[str, list[dict]] = {}
        self._max = max_messages
        self._lock = threading.Lock()

    def get(self, session_id: str) -> list[dict]:
        with self._lock:
            return list(self._sessions.get(session_id, []))

    def append(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            hist = self._sessions.setdefault(session_id, [])
            hist.append({"role": role, "content": content})
            if len(hist) > self._max:
                self._sessions[session_id] = hist[-self._max:]

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
