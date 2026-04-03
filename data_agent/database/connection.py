"""Database connection management via SQLAlchemy."""

from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


class QueryResult:
    """Structured query result."""

    def __init__(
        self,
        columns: list[str],
        rows: list[list],
        row_count: int,
        truncated: bool = False,
    ):
        self.columns = columns
        self.rows = rows
        self.row_count = row_count
        self.truncated = truncated

    def to_dict(self) -> dict:
        return {
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "truncated": self.truncated,
        }

    def to_markdown_table(self, max_col_width: int = 40) -> str:
        """Format as a markdown table."""
        if not self.rows:
            return "(空结果集)"

        def truncate(val: str) -> str:
            s = str(val)
            return s[:max_col_width] + "..." if len(s) > max_col_width else s

        header = "| " + " | ".join(self.columns) + " |"
        separator = "| " + " | ".join("---" for _ in self.columns) + " |"
        body_lines = []
        for row in self.rows:
            line = "| " + " | ".join(truncate(v) for v in row) + " |"
            body_lines.append(line)

        parts = [header, separator, *body_lines]
        if self.truncated:
            parts.append(f"\n(结果已截断，共 {self.row_count} 行)")
        return "\n".join(parts)


class DatabaseManager:
    """Manage database connections and execute SQL queries."""

    def __init__(self, connection_string: str, query_timeout: int = 30):
        self.connection_string = connection_string
        self.query_timeout = query_timeout
        self._engine: Engine | None = None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(
                self.connection_string,
                pool_pre_ping=True,
            )
        return self._engine

    def test_connection(self) -> bool:
        """Test whether the database connection is working."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    def execute_query(self, sql: str, max_rows: int = 500) -> QueryResult:
        """Execute a read-only SQL query and return structured results."""
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            columns = list(result.keys())
            all_rows = result.fetchmany(max_rows + 1)

            truncated = len(all_rows) > max_rows
            rows = [list(row) for row in all_rows[:max_rows]]

            if truncated:
                count_sql = f"SELECT COUNT(*) FROM ({sql}) AS _subq"
                try:
                    count_result = conn.execute(text(count_sql))
                    total = count_result.scalar()
                except Exception:
                    total = max_rows + 1
            else:
                total = len(rows)

        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=total,
            truncated=truncated,
        )

    def dispose(self) -> None:
        """Close the engine and release connections."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None
