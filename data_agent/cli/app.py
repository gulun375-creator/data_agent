"""CLI interactive interface using Rich and prompt_toolkit."""

from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from data_agent.agent.agent import DataAgent
from data_agent.config.schema_loader import SchemaLoader
from data_agent.config.settings import AgentConfig
from data_agent.database.connection import DatabaseManager

console = Console()


def sql_confirmation_callback(sql: str) -> str:
    """Interactive SQL confirmation in the terminal."""
    console.print()
    console.print(
        Panel(
            Syntax(sql, "sql", theme="monokai", line_numbers=False),
            title="[bold yellow]生成的 SQL[/bold yellow]",
            border_style="yellow",
        )
    )
    console.print()

    while True:
        choice = console.input(
            "[bold]确认执行？[/bold] [green]\\[Y]确认[/green]  "
            "[cyan]\\[E]编辑[/cyan]  [red]\\[N]取消[/red]: "
        ).strip().upper()

        if choice in ("Y", "YES", ""):
            return "confirm"
        if choice in ("N", "NO"):
            return "cancel"
        if choice in ("E", "EDIT"):
            console.print("[cyan]请输入修改后的 SQL（输入空行结束）:[/cyan]")
            lines: list[str] = []
            while True:
                line = console.input()
                if not line:
                    break
                lines.append(line)
            modified = "\n".join(lines).strip()
            if modified:
                return modified
            console.print("[yellow]未输入修改内容，请重新选择。[/yellow]")


def run_cli(config: AgentConfig) -> None:
    """Run the interactive CLI loop."""
    console.print()
    console.print(
        Panel(
            "[bold]Data Agent v0.1.0[/bold]\n"
            "数据分析 AI 助手 · 输入问题开始分析\n"
            "输入 [cyan]/help[/cyan] 查看帮助  "
            "输入 [cyan]/exit[/cyan] 退出",
            border_style="blue",
        )
    )

    schema_loader = SchemaLoader(config.schema_dir)
    try:
        schema_loader.load_all()
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Schema 加载失败: {e}[/red]")
        return

    source_name = schema_loader.get_first_source_name()
    schema_config = schema_loader.get_config(source_name)

    db_manager = DatabaseManager(
        connection_string=schema_config.data_source.connection,
        query_timeout=config.database.query_timeout,
    )

    if not db_manager.test_connection():
        console.print("[red]数据库连接失败，请检查配置。[/red]")
        return

    table_count = len(schema_config.tables)
    table_names = ", ".join(t.table_name for t in schema_config.tables)
    console.print(
        Panel(
            f"数据源: [bold]{schema_config.data_source.name}[/bold] "
            f"({schema_config.data_source.type})\n"
            f"已加载: {table_count} 张表 ({table_names})",
            border_style="green",
        )
    )

    agent = DataAgent(
        config=config,
        schema_loader=schema_loader,
        db_manager=db_manager,
        source_name=source_name,
        confirmation_callback=sql_confirmation_callback,
    )

    session = PromptSession(history=InMemoryHistory())

    while True:
        try:
            user_input = session.prompt("\nYou > ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            if _handle_command(user_input, agent, schema_loader, source_name):
                continue
            else:
                break

        try:
            with console.status("[bold green]思考中...[/bold green]"):
                response = agent.chat(user_input)
            console.print()
            console.print(Markdown(response))
        except Exception as e:
            console.print(f"\n[red]出错了: {e}[/red]")

    agent.dispose()
    console.print("\n[dim]再见！[/dim]")


def _handle_command(
    command: str,
    agent: DataAgent,
    schema_loader: SchemaLoader,
    source_name: str,
) -> bool:
    """Handle slash commands. Returns True to continue, False to exit."""
    parts = command.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "/exit":
        return False

    if cmd == "/help":
        console.print(
            Panel(
                "[cyan]/tables[/cyan]         列出所有可用表\n"
                "[cyan]/schema <表名>[/cyan]  查看表的详细结构\n"
                "[cyan]/history[/cyan]        查看对话历史\n"
                "[cyan]/clear[/cyan]          清除当前对话上下文\n"
                "[cyan]/exit[/cyan]           退出程序",
                title="[bold]命令帮助[/bold]",
                border_style="cyan",
            )
        )
        return True

    if cmd == "/tables":
        summary = schema_loader.get_all_tables_summary(source_name)
        console.print(f"\n{summary}")
        return True

    if cmd == "/schema":
        if not arg:
            console.print("[yellow]用法: /schema <表名>[/yellow]")
            return True
        try:
            detail = schema_loader.get_table_detail(source_name, arg.strip())
            console.print(f"\n{detail}")
        except KeyError as e:
            console.print(f"[red]{e}[/red]")
        return True

    if cmd == "/history":
        from langchain_core.messages import HumanMessage

        messages = agent.chat_memory.get_messages("default")
        if not messages:
            console.print("[dim]暂无对话历史。[/dim]")
        else:
            for msg in messages:
                role = "You" if isinstance(msg, HumanMessage) else "Agent"
                console.print(f"[bold]{role}:[/bold] {msg.content[:200]}")
        return True

    if cmd == "/clear":
        agent.chat_memory.clear("default")
        console.print("[green]对话上下文已清除。[/green]")
        return True

    console.print(f"[yellow]未知命令: {cmd}。输入 /help 查看帮助。[/yellow]")
    return True
