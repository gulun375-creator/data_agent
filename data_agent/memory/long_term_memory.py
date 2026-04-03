"""Long-term memory backed by FAISS vector store."""

from __future__ import annotations

import time
from pathlib import Path


class LongTermMemory:
    """Persistent memory using FAISS for semantic search across sessions."""

    def __init__(self, persist_dir: str, api_key: str = ""):
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self._api_key = api_key
        self._vectorstore = None
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """Lazy-initialize the vector store. Returns False if unavailable."""
        if self._initialized:
            return self._vectorstore is not None
        self._initialized = True

        if not self._api_key:
            return False

        try:
            from langchain_community.vectorstores import FAISS
            from langchain_openai import OpenAIEmbeddings

            embeddings = OpenAIEmbeddings(api_key=self._api_key)
            index_path = self.persist_dir / "index.faiss"

            if index_path.exists():
                self._vectorstore = FAISS.load_local(
                    str(self.persist_dir),
                    embeddings,
                    allow_dangerous_deserialization=True,
                )
            else:
                self._vectorstore = FAISS.from_texts(
                    ["Data Agent 长期记忆已初始化"],
                    embeddings,
                    metadatas=[{"type": "system", "timestamp": time.time()}],
                )
                self._vectorstore.save_local(str(self.persist_dir))
            return True
        except Exception:
            return False

    def store(self, content: str, metadata: dict | None = None) -> None:
        """Store a piece of information into long-term memory."""
        if not self._ensure_initialized():
            return

        meta = metadata or {}
        meta["timestamp"] = time.time()

        self._vectorstore.add_texts([content], metadatas=[meta])

    def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        """Retrieve relevant memories by semantic similarity."""
        if not self._ensure_initialized():
            return []

        try:
            docs = self._vectorstore.similarity_search(query, k=top_k)
            return [doc.page_content for doc in docs]
        except Exception:
            return []

    def persist(self) -> None:
        """Save the vector store to disk."""
        if self._vectorstore is not None:
            try:
                self._vectorstore.save_local(str(self.persist_dir))
            except Exception:
                pass
