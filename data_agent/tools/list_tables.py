"""Tool: list all available tables."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from data_agent.config.schema_loader import SchemaLoader


def create_list_tables_tool(schema_loader: SchemaLoader, source_name: str):
    """Create a list_tables tool bound to a specific schema loader and source."""

    @tool
    def list_tables() -> str:
        """列出所有可用的数据表及其描述。在需要了解有哪些数据可以查询时使用此工具。"""
        return schema_loader.get_all_tables_summary(source_name)

    return list_tables
