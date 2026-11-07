# app/memory.py
from typing import Dict, List, Any

class ChatMessage:
    def __init__(self, role: str, content: str):
        self.type = role  # "human" or "ai"
        self.content = content

class SessionMemoryManager:
    """Manages chat history across multiple turns keyed by session_id without deprecations."""
    def __init__(self):
        self.sessions: Dict[str, List[ChatMessage]] = {}

    def get_session_history(self, session_id: str) -> List[ChatMessage]:
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        return self.sessions[session_id]

    def add_user_message(self, session_id: str, message: str):
        history = self.get_session_history(session_id)
        history.append(ChatMessage("human", message))

    def add_ai_message(self, session_id: str, message: str):
        history = self.get_session_history(session_id)
        history.append(ChatMessage("ai", message))

    def get_formatted_history(self, session_id: str) -> str:
        history = self.get_session_history(session_id)
        formatted = []
        for msg in history:
            role = "User" if msg.type == "human" else "Assistant"
            formatted.append(f"{role}: {msg.content}")
        return "\n".join(formatted)

session_manager = SessionMemoryManager()