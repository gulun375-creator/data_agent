"""SQL security validation."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ValidationResult:
    is_valid: bool
    reason: str = ""
    sql_type: str = "SELECT"


class SQLValidator:
    """Validate SQL statements for safety before execution."""

    BLOCKED_KEYWORDS = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "TRUNCATE",
        "CREATE",
        "GRANT",
        "REVOKE",
        "EXEC",
        "EXECUTE",
        "CALL",
        "MERGE",
        "REPLACE",
        "LOAD",
        "INTO OUTFILE",
        "INTO DUMPFILE",
    ]

    BLOCKED_PATTERN = re.compile(
        r"\b(" + "|".join(BLOCKED_KEYWORDS) + r")\b",
        re.IGNORECASE,
    )

    def validate(self, sql: str) -> ValidationResult:
        """Validate that the SQL is a safe, read-only query."""
        normalized = self.normalize(sql)

        if not normalized:
            return ValidationResult(
                is_valid=False,
                reason="SQL 语句为空",
                sql_type="EMPTY",
            )

        match = self.BLOCKED_PATTERN.search(normalized)
        if match:
            keyword = match.group(1).upper()
            return ValidationResult(
                is_valid=False,
                reason=f"检测到危险操作关键词: {keyword}。仅允许 SELECT 查询。",
                sql_type=keyword,
            )

        stripped = normalized.lstrip()
        if not stripped.upper().startswith("SELECT") and not stripped.upper().startswith("WITH"):
            return ValidationResult(
                is_valid=False,
                reason="仅允许 SELECT 或 WITH (CTE) 查询语句。",
                sql_type="OTHER",
            )

        if ";" in normalized:
            parts = [p.strip() for p in normalized.split(";") if p.strip()]
            if len(parts) > 1:
                return ValidationResult(
                    is_valid=False,
                    reason="不允许多条 SQL 语句，请每次只执行一条查询。",
                    sql_type="MULTI",
                )

        return ValidationResult(is_valid=True, sql_type="SELECT")

    def normalize(self, sql: str) -> str:
        """Normalize SQL by removing comments and extra whitespace."""
        sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
        sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
        sql = re.sub(r"\s+", " ", sql).strip()
        return sql
