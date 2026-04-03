"""Session-scoped chat memory management."""

from __future__ import annotations

import json
from pathlib import Path

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


class ChatMemory:
    """Manage per-session conversation history."""

    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self._sessions: dict[str, list[BaseMessage]] = {}

    def get_messages(self, session_id: str) -> list[BaseMessage]:
        """Get conversation history for a session."""
        return list(self._sessions.get(session_id, []))

    def add_message(self, session_id: str, message: BaseMessage) -> None:
        """Add a message to the session history, trimming if needed."""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        self._sessions[session_id].append(message)
        if len(self._sessions[session_id]) > self.max_messages:
            self._sessions[session_id] = self._sessions[session_id][
                -self.max_messages :
            ]

    def clear(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        self._sessions.pop(session_id, None)

    def save_to_file(self, session_id: str, path: str) -> None:
        """Persist a session's history to a JSON file."""
        messages = self._sessions.get(session_id, [])
        data = [
            {"type": type(m).__name__, "content": m.content} for m in messages
        ]
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_file(self, session_id: str, path: str) -> None:
        """Restore a session's history from a JSON file."""
        file_path = Path(path)
        if not file_path.exists():
            return
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        messages: list[BaseMessage] = []
        for item in data:
            if item["type"] == "HumanMessage":
                messages.append(HumanMessage(content=item["content"]))
            elif item["type"] == "AIMessage":
                messages.append(AIMessage(content=item["content"]))
        self._sessions[session_id] = messages
