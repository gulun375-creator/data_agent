"""Core Data Agent built on LangChain."""

from __future__ import annotations

from typing import Callable

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from data_agent.agent.prompts import SYSTEM_PROMPT_TEMPLATE
from data_agent.config.schema_loader import SchemaLoader
from data_agent.config.settings import AgentConfig
from data_agent.database.connection import DatabaseManager
from data_agent.database.sql_validator import SQLValidator
from data_agent.memory.chat_memory import ChatMemory
from data_agent.memory.long_term_memory import LongTermMemory
from data_agent.tools.execute_sql import create_execute_sql_tool
from data_agent.tools.get_sample_data import create_get_sample_data_tool
from data_agent.tools.get_schema import create_get_schema_tool
from data_agent.tools.list_tables import create_list_tables_tool


class DataAgent:
    """Data analysis agent powered by LLM."""

    def __init__(
        self,
        config: AgentConfig,
        schema_loader: SchemaLoader,
        db_manager: DatabaseManager,
        source_name: str,
        confirmation_callback: Callable[[str], str] | None = None,
    ):
        self.config = config
        self.schema_loader = schema_loader
        self.db_manager = db_manager
        self.source_name = source_name
        self.sql_validator = SQLValidator()
        self.chat_memory = ChatMemory(
            max_messages=config.memory.chat_history_max_messages,
        )
        self.long_term_memory = LongTermMemory(
            persist_dir=config.memory.long_term_memory_dir,
            api_key=config.openai_api_key,
        )

        self.llm = ChatOpenAI(
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            api_key=config.openai_api_key,
        )

        self.tools = self._build_tools(confirmation_callback)
        self.agent = self._build_agent()

    def _build_tools(self, confirmation_callback: Callable[[str], str] | None) -> list:
        return [
            create_list_tables_tool(self.schema_loader, self.source_name),
            create_get_schema_tool(self.schema_loader, self.source_name),
            create_execute_sql_tool(
                db_manager=self.db_manager,
                sql_validator=self.sql_validator,
                confirmation_callback=confirmation_callback,
                max_rows=self.config.database.max_query_rows,
            ),
            create_get_sample_data_tool(
                db_manager=self.db_manager,
                schema_loader=self.schema_loader,
                source_name=self.source_name,
            ),
        ]

    def _build_agent(self):
        schema_context = self.schema_loader.get_all_tables_summary(self.source_name)

        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT_TEMPLATE),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        llm_with_tools = self.llm.bind_tools(self.tools)

        from langchain.agents import AgentExecutor, create_tool_calling_agent

        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
            max_iterations=10,
            handle_parsing_errors=True,
        ), schema_context

    def chat(self, user_input: str, session_id: str = "default") -> str:
        """Process user input and return agent response."""
        agent_executor, schema_context = self.agent

        memory_results = self.long_term_memory.retrieve(user_input)
        if memory_results:
            memory_context = "## 相关历史记忆\n" + "\n".join(
                f"- {m}" for m in memory_results
            )
        else:
            memory_context = ""

        chat_history = self.chat_memory.get_messages(session_id)

        response = agent_executor.invoke({
            "input": user_input,
            "chat_history": chat_history,
            "schema_context": schema_context,
            "memory_context": memory_context,
        })

        output = response["output"]

        self.chat_memory.add_message(session_id, HumanMessage(content=user_input))
        from langchain_core.messages import AIMessage
        self.chat_memory.add_message(session_id, AIMessage(content=output))

        self.long_term_memory.store(
            content=f"用户问: {user_input}\n分析结果: {output[:500]}",
            metadata={"type": "query_pattern", "session_id": session_id},
        )

        return output

    def dispose(self) -> None:
        """Clean up resources."""
        self.long_term_memory.persist()
        self.db_manager.dispose()
