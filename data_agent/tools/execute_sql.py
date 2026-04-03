"""Tool: execute SQL query with safety validation and user confirmation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from langchain_core.tools import tool

if TYPE_CHECKING:
    from data_agent.database.connection import DatabaseManager
    from data_agent.database.sql_validator import SQLValidator


def create_execute_sql_tool(
    db_manager: DatabaseManager,
    sql_validator: SQLValidator,
    confirmation_callback: Callable[[str], str] | None = None,
    max_rows: int = 500,
):
    """Create an execute_sql tool with injected dependencies.

    Args:
        db_manager: Database connection manager.
        sql_validator: SQL safety validator.
        confirmation_callback: Callback to request user confirmation.
            Receives SQL string, returns "confirm" / "cancel" / modified SQL.
            If None, SQL executes without confirmation.
        max_rows: Maximum rows to return.
    """

    @tool
    def execute_sql(sql: str) -> str:
        """执行 SQL 查询并返回结果。仅支持 SELECT 查询。
        在需要从数据库获取数据时使用此工具。

        Args:
            sql: 要执行的 SQL 查询语句（仅支持 SELECT）
        """
        validation = sql_validator.validate(sql)
        if not validation.is_valid:
            return f"SQL 校验失败: {validation.reason}"

        if confirmation_callback is not None:
            result = confirmation_callback(sql)
            if result == "cancel":
                return "用户已取消本次查询。"
            if result != "confirm":
                sql = result
                re_validation = sql_validator.validate(sql)
                if not re_validation.is_valid:
                    return f"修改后的 SQL 校验失败: {re_validation.reason}"

        try:
            query_result = db_manager.execute_query(sql, max_rows=max_rows)
            return query_result.to_markdown_table()
        except Exception as e:
            return f"SQL 执行出错: {e}"

    return execute_sql
