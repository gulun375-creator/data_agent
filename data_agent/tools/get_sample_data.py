"""Tool: get sample data from a table."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.tools import tool

if TYPE_CHECKING:
    from data_agent.config.schema_loader import SchemaLoader
    from data_agent.database.connection import DatabaseManager


def create_get_sample_data_tool(
    db_manager: DatabaseManager,
    schema_loader: SchemaLoader,
    source_name: str,
):
    """Create a get_sample_data tool bound to a specific DB and schema."""

    @tool
    def get_sample_data(table_name: str, limit: int = 5) -> str:
        """获取指定表的示例数据，帮助理解数据的实际内容和格式。

        Args:
            table_name: 要查询的表名
            limit: 返回的行数，默认 5 行
        """
        try:
            schema_loader.get_table(source_name, table_name)
        except KeyError as e:
            return str(e)

        sql = f"SELECT * FROM {table_name} LIMIT {limit}"
        try:
            result = db_manager.execute_query(sql, max_rows=limit)
            return result.to_markdown_table()
        except Exception as e:
            return f"查询出错: {e}"

    return get_sample_data
