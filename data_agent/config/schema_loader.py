"""Schema configuration loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    name: str
    type: str
    description: str
    is_primary_key: bool = False
    foreign_key: str | None = None
    enum_values: dict[str, str] | None = None


class TableSchema(BaseModel):
    table_name: str
    description: str
    columns: list[ColumnSchema]


class Relationship(BaseModel):
    from_field: str = Field(alias="from")
    to: str
    type: str
    description: str

    model_config = {"populate_by_name": True}


class DataSource(BaseModel):
    name: str
    type: str
    connection: str


class SchemaConfig(BaseModel):
    data_source: DataSource
    tables: list[TableSchema]
    relationships: list[Relationship] = []


class SchemaLoader:
    """Load and manage Schema configurations from YAML/JSON files."""

    def __init__(self, schema_dir: str):
        self.schema_dir = Path(schema_dir)
        self.configs: dict[str, SchemaConfig] = {}

    def load_all(self) -> None:
        """Scan the directory for all .yaml/.yml/.json files and load them."""
        if not self.schema_dir.exists():
            raise FileNotFoundError(f"Schema directory not found: {self.schema_dir}")

        for path in sorted(self.schema_dir.iterdir()):
            if path.suffix in (".yaml", ".yml"):
                self._load_file(path, loader=yaml.safe_load)
            elif path.suffix == ".json":
                self._load_file(path, loader=json.loads)

        if not self.configs:
            raise ValueError(f"No schema files found in {self.schema_dir}")

    def _load_file(self, path: Path, loader: callable) -> None:
        with open(path) as f:
            raw = loader(f.read()) if path.suffix == ".json" else yaml.safe_load(f)
        config = SchemaConfig(**raw)
        self.configs[config.data_source.name] = config

    def get_config(self, source_name: str) -> SchemaConfig:
        """Get schema config by data source name."""
        if source_name not in self.configs:
            available = ", ".join(self.configs.keys())
            raise KeyError(
                f"Data source '{source_name}' not found. Available: {available}"
            )
        return self.configs[source_name]

    def get_table(self, source_name: str, table_name: str) -> TableSchema:
        """Get a specific table schema."""
        config = self.get_config(source_name)
        for table in config.tables:
            if table.table_name == table_name:
                return table
        available = ", ".join(t.table_name for t in config.tables)
        raise KeyError(
            f"Table '{table_name}' not found in '{source_name}'. Available: {available}"
        )

    def get_first_source_name(self) -> str:
        """Get the first available data source name."""
        if not self.configs:
            raise ValueError("No schema configs loaded")
        return next(iter(self.configs))

    def get_all_tables_summary(self, source_name: str) -> str:
        """Generate a summary of all tables for the System Prompt."""
        config = self.get_config(source_name)
        lines: list[str] = []
        for i, table in enumerate(config.tables, 1):
            cols = ", ".join(c.name for c in table.columns)
            lines.append(f"{i}. {table.table_name} - {table.description}（字段: {cols}）")
        return "\n".join(lines)

    def get_table_detail(self, source_name: str, table_name: str) -> str:
        """Generate detailed description of a table including columns, enums, and relationships."""
        config = self.get_config(source_name)
        table = self.get_table(source_name, table_name)

        lines: list[str] = [
            f"表名: {table.table_name}",
            f"描述: {table.description}",
            "字段:",
        ]

        for col in table.columns:
            parts = [f"  - {col.name} ({col.type})"]
            if col.is_primary_key:
                parts.append(" [主键]")
            parts.append(f": {col.description}")
            if col.enum_values:
                enum_str = ", ".join(f"{k}: {v}" for k, v in col.enum_values.items())
                parts.append(f" {{{enum_str}}}")
            if col.foreign_key:
                parts.append(f" [外键 -> {col.foreign_key}]")
            lines.append("".join(parts))

        related = [
            r
            for r in config.relationships
            if r.from_field.startswith(f"{table_name}.")
            or r.to.startswith(f"{table_name}.")
        ]
        if related:
            lines.append("关联关系:")
            for r in related:
                lines.append(
                    f"  - {r.from_field} -> {r.to} ({r.type}): {r.description}"
                )

        return "\n".join(lines)

    def get_all_tables_detail(self, source_name: str) -> str:
        """Generate detailed descriptions for all tables."""
        config = self.get_config(source_name)
        sections = [
            self.get_table_detail(source_name, t.table_name)
            for t in config.tables
        ]
        return "\n\n".join(sections)
