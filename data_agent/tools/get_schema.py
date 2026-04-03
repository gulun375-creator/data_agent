"""Tool: get detailed schema for a table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from data_agent.config.schema_loader import SchemaLoader


def create_get_schema_tool(schema_loader: SchemaLoader, source_name: str):
    """Create a get_schema tool bound to a specific schema loader and source."""

    @tool
    def get_schema(table_name: str) -> str:
        """获取指定数据表的详细结构信息，包括字段名、类型、描述、枚举值等。
        在需要了解表的具体字段以生成 SQL 时使用此工具。

        Args:
            table_name: 要查询的表名
        """
        try:
            return schema_loader.get_table_detail(source_name, table_name)
        except KeyError as e:
            return str(e)

    return get_schema
