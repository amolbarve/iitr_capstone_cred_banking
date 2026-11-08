# app/memory.py
from typing import Dict
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.runnables import RunnableLambda
from langchain_core.messages import HumanMessage, AIMessage

# In-memory store for session histories
session_store: Dict[str, InMemoryChatMessageHistory] = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    """Returns the InMemoryChatMessageHistory instance for a given session_id."""
    if session_id not in session_store:
        session_store[session_id] = InMemoryChatMessageHistory()
    return session_store[session_id]

class SessionMemoryManager:
    """Manages chat history using LangChain's InMemoryChatMessageHistory and RunnableWithMessageHistory."""

    def __init__(self):
        # A lightweight runnable lambda that formats incoming inputs for chains
        self._runnable = RunnableLambda(lambda x: x.get("input", ""))
        self.runnable_with_history = RunnableWithMessageHistory(
            self._runnable,
            get_session_history=get_session_history,
            input_messages_key="input",
            history_messages_key="history"
        )

    def get_session_history(self, session_id: str) -> InMemoryChatMessageHistory:
        return get_session_history(session_id)

    def add_user_message(self, session_id: str, message: str):
        history = get_session_history(session_id)
        history.add_user_message(message)

    def add_ai_message(self, session_id: str, message: str):
        history = get_session_history(session_id)
        history.add_ai_message(message)

    def get_formatted_history(self, session_id: str) -> str:
        history = get_session_history(session_id)
        formatted = []
        for msg in history.messages:
            role = "User" if isinstance(msg, HumanMessage) else "Assistant"
            formatted.append(f"{role}: {msg.content}")
        return "\n".join(formatted)

    def clear_session(self, session_id: str):
        if session_id in session_store:
            session_store[session_id].clear()

session_manager = SessionMemoryManager()