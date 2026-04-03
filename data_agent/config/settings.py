"""Application configuration management."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o"
    temperature: float = 0
    max_tokens: int = 4096


class DatabaseConfig(BaseModel):
    max_query_rows: int = 500
    query_timeout: int = 30


class MemoryConfig(BaseModel):
    chat_history_max_messages: int = 50
    long_term_memory_dir: str = "./data/memory"
    long_term_memory_top_k: int = 5


class AgentConfig(BaseModel):
    llm: LLMConfig = Field(default_factory=LLMConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    schema_dir: str = "./schemas"
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    openai_api_key: str = ""

    def model_post_init(self, __context: object) -> None:
        if not self.openai_api_key:
            self.openai_api_key = os.getenv("OPENAI_API_KEY", "")


def load_config(config_path: str | None = None) -> AgentConfig:
    """Load configuration from YAML file, falling back to defaults.

    Priority: YAML file values > environment variables > defaults.
    """
    if config_path is None:
        config_path = os.getenv("DATA_AGENT_CONFIG", "config/settings.yaml")

    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        return AgentConfig(**raw)

    return AgentConfig()
