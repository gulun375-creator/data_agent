# Data Agent - 技术方案

> **项目名称**：Data Agent  
> **文档版本**：v1.0  
> **创建日期**：2026-04-02  
> **最后更新**：2026-04-02  
> **关联文档**：[需求文档](./requirements.md)

---

## 1. 技术概览

### 1.1 系统定位

基于 LLM 的数据分析 AI Agent，核心链路为：**Schema 配置 → 自然语言理解 → SQL 生成 → 用户确认 → 数据库执行 → 结果解读与可视化**。

### 1.2 技术栈

| 组件 | 选型 | 版本要求 |
|------|------|---------|
| 语言 | Python | >= 3.11 |
| LLM 框架 | LangChain | latest |
| LLM 模型 | OpenAI GPT (gpt-4o) | API |
| 数据库访问 | SQLAlchemy | >= 2.0 |
| 向量数据库 | FAISS | latest |
| 数据处理 | Pandas | latest |
| 配置管理 | Pydantic | >= 2.0 |
| CLI 交互 | Rich | latest |

> 前端框架和可视化库在 MVP 后期确定，MVP 阶段先以 CLI 交互验证核心链路。

### 1.3 设计原则

- **Schema First**：所有数据分析都基于预定义的 Schema，Agent 不直接探索数据库
- **SQL Only**：MVP 阶段数据分析全部通过 SQL 完成，不引入 Python 代码执行沙箱
- **Human in the Loop**：SQL 执行前必须经过用户确认
- **工具化**：Agent 的数据操作能力全部封装为 Tool，通过 LangChain Tool Calling 调度
- **配置驱动**：数据源连接、Schema 定义、Agent 行为均通过配置文件管理

---

## 2. 系统架构

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        交互层                                │
│                CLI (MVP) / Web UI (后续)                      │
│            用户输入 / SQL 确认 / 结果展示                      │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    Agent 核心引擎                             │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                  AgentExecutor                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │  │
│  │  │ System Prompt │  │ Chat Memory  │  │ Tool Router │  │  │
│  │  │ (Schema 注入) │  │ (对话上下文)  │  │ (工具调度)   │  │  │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐   │
│  │list_tables│ │get_schema│ │execute_sql│ │get_sample_data│  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────┘   │
│                                                              │
└───────────┬──────────────────┬───────────────────────────────┘
            │                  │
┌───────────▼───────┐  ┌──────▼──────────────────────────────┐
│   Schema 配置层    │  │           数据库访问层                │
│  ┌─────────────┐  │  │  ┌──────────────────────────────┐   │
│  │ YAML/JSON   │  │  │  │     SQLAlchemy Engine         │   │
│  │ Schema 文件  │  │  │  │  ┌────────┐  ┌───────────┐   │   │
│  └─────────────┘  │  │  │  │ MySQL  │  │ PostgreSQL│   │   │
│  ┌─────────────┐  │  │  │  └────────┘  └───────────┘   │   │
│  │ SchemaLoader│  │  │  │  ┌────────┐                   │   │
│  │ & Validator │  │  │  │  │ SQLite │                   │   │
│  └─────────────┘  │  │  │  └────────┘                   │   │
└───────────────────┘  │  └──────────────────────────────┘   │
                       └─────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                     持久化层                                  │
│  ┌──────────────────┐  ┌─────────────────────────────────┐  │
│  │  对话历史存储      │  │  长期记忆 (FAISS)                │  │
│  │  (SQLite/JSON)    │  │  用户偏好 / 分析结论 / 常用查询   │  │
│  └──────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 模块划分

```
data_agent/
├── main.py                     # 应用入口
├── config/
│   ├── settings.py             # 全局配置（LLM、数据库等）
│   └── schema_loader.py        # Schema 配置加载与校验
├── agent/
│   ├── agent.py                # Agent 核心构建（AgentExecutor）
│   ├── prompts.py              # System Prompt 模板
│   └── callbacks.py            # SQL 确认等回调处理
├── tools/
│   ├── list_tables.py          # list_tables 工具
│   ├── get_schema.py           # get_schema 工具
│   ├── execute_sql.py          # execute_sql 工具
│   └── get_sample_data.py      # get_sample_data 工具
├── database/
│   ├── connection.py           # 数据库连接管理（SQLAlchemy）
│   └── sql_validator.py        # SQL 安全校验
├── memory/
│   ├── chat_memory.py          # 对话历史管理
│   └── long_term_memory.py     # 长期记忆（FAISS）
├── cli/
│   └── app.py                  # CLI 交互界面
└── schemas/                    # Schema 配置文件目录
    └── example.yaml            # 示例 Schema
```

---

## 3. 核心模块设计

### 3.1 Schema 配置层

#### 3.1.1 Schema 文件格式

采用 YAML 作为主要配置格式（比 JSON 更适合手动编辑），同时兼容 JSON。

**`schemas/example.yaml`**

```yaml
data_source:
  name: "电商业务库"
  type: mysql                         # mysql / postgresql / sqlite
  connection: "mysql+pymysql://user:pass@host:3306/ecommerce"

tables:
  - table_name: orders
    description: "订单主表，记录所有用户订单信息"
    columns:
      - name: id
        type: BIGINT
        description: "订单ID，主键"
        is_primary_key: true

      - name: user_id
        type: BIGINT
        description: "用户ID，关联 users 表"
        foreign_key: users.id

      - name: total_amount
        type: "DECIMAL(10,2)"
        description: "订单总金额（单位：元）"

      - name: status
        type: TINYINT
        description: "订单状态"
        enum_values:
          0: "待支付"
          1: "已支付"
          2: "已发货"
          3: "已完成"
          4: "已取消"

      - name: created_at
        type: DATETIME
        description: "订单创建时间"

  - table_name: users
    description: "用户表"
    columns:
      - name: id
        type: BIGINT
        description: "用户ID，主键"
        is_primary_key: true

      - name: name
        type: "VARCHAR(100)"
        description: "用户姓名"

      - name: region
        type: "VARCHAR(50)"
        description: "所在地区"

      - name: created_at
        type: DATETIME
        description: "注册时间"

relationships:
  - from: orders.user_id
    to: users.id
    type: many_to_one
    description: "每个订单属于一个用户"
```

#### 3.1.2 Schema 数据模型

使用 Pydantic 进行校验和类型约束。

```python
from pydantic import BaseModel

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
    from_: str                          # 使用 alias "from"
    to: str
    type: str                           # many_to_one / one_to_many / many_to_many
    description: str

class DataSource(BaseModel):
    name: str
    type: str                           # mysql / postgresql / sqlite
    connection: str

class SchemaConfig(BaseModel):
    data_source: DataSource
    tables: list[TableSchema]
    relationships: list[Relationship] = []
```

#### 3.1.3 Schema 加载器

```python
class SchemaLoader:
    """从 YAML/JSON 文件加载并校验 Schema 配置"""

    def __init__(self, schema_dir: str):
        self.schema_dir = schema_dir
        self.configs: dict[str, SchemaConfig] = {}

    def load_all(self) -> None:
        """扫描目录下所有 .yaml/.json 文件并加载"""

    def get_config(self, source_name: str) -> SchemaConfig:
        """按数据源名称获取配置"""

    def get_table(self, source_name: str, table_name: str) -> TableSchema:
        """获取指定表的 Schema"""

    def get_all_tables_summary(self, source_name: str) -> str:
        """生成所有表的摘要文本，用于注入 System Prompt"""

    def get_table_detail(self, source_name: str, table_name: str) -> str:
        """生成单张表的详细描述文本，包含字段、枚举、关系"""
```

### 3.2 数据库访问层

#### 3.2.1 连接管理

基于 SQLAlchemy 封装统一的数据库连接管理，支持 MySQL / PostgreSQL / SQLite。

```python
from sqlalchemy import create_engine, text

class DatabaseManager:
    """管理数据库连接，执行 SQL 查询"""

    def __init__(self, connection_string: str):
        self.engine = create_engine(connection_string)

    def execute_query(self, sql: str, max_rows: int = 500) -> dict:
        """
        执行只读 SQL 查询，返回结构化结果。

        返回格式:
        {
            "columns": ["col1", "col2", ...],
            "rows": [[val1, val2, ...], ...],
            "row_count": 123,
            "truncated": false
        }
        """

    def test_connection(self) -> bool:
        """测试数据库连接是否正常"""
```

#### 3.2.2 SQL 安全校验

在执行前对 SQL 进行安全检查，拦截危险操作。

```python
class SQLValidator:
    """SQL 安全校验器"""

    BLOCKED_KEYWORDS = [
        "DROP", "DELETE", "UPDATE", "INSERT", "ALTER",
        "TRUNCATE", "CREATE", "GRANT", "REVOKE", "EXEC"
    ]

    def validate(self, sql: str) -> ValidationResult:
        """
        校验 SQL 是否安全。

        返回:
        - is_valid: bool
        - reason: str (如果不合法，说明原因)
        - sql_type: str ("SELECT" / "OTHER")
        """

    def normalize(self, sql: str) -> str:
        """标准化 SQL（去除注释、多余空白等）"""
```

### 3.3 Agent 核心引擎

#### 3.3.1 System Prompt 设计

System Prompt 是 Agent 行为的核心控制点，需要注入 Schema 上下文。

```python
SYSTEM_PROMPT_TEMPLATE = """你是一个专业的数据分析助手。你的任务是帮助用户通过自然语言分析数据库中的数据。

## 你的能力
- 理解用户的数据分析需求，生成准确的 SQL 查询
- 解读查询结果，提供有价值的数据洞察
- 支持多轮对话，逐步深入分析

## 可用的数据表

{schema_context}

## 工作流程
1. 理解用户问题，确定需要查询的表和字段
2. 使用 get_schema 工具获取表的详细结构（如需要）
3. 生成 SQL 查询语句
4. 使用 execute_sql 工具执行查询
5. 解读结果，用清晰的自然语言回答用户

## 规则
- 只生成 SELECT 查询，不生成任何修改数据的语句
- 充分利用字段描述和枚举值映射来理解业务含义
- 结果中包含具体数字时，给出百分比、趋势等解读
- 如果用户的问题不明确，主动询问澄清
- 查询结果较多时，默认展示 Top 10 并说明
"""
```

#### 3.3.2 Agent 构建

```python
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

class DataAgent:
    """数据分析 Agent 核心类"""

    def __init__(self, config: AgentConfig):
        self.config = config
        self.schema_loader = SchemaLoader(config.schema_dir)
        self.db_manager = DatabaseManager(config.db_connection)
        self.sql_validator = SQLValidator()
        self.memory = ChatMemory()
        self.long_term_memory = LongTermMemory(config.memory_dir)

        self.llm = ChatOpenAI(
            model=config.model_name,            # gpt-4o
            temperature=0,                      # 数据分析场景用低 temperature
            api_key=config.openai_api_key,
        )

        self.tools = self._build_tools()
        self.agent_executor = self._build_agent()

    def _build_tools(self) -> list:
        """构建 Agent 可用的工具列表"""

    def _build_agent(self) -> AgentExecutor:
        """构建 LangChain AgentExecutor"""
        schema_context = self.schema_loader.get_all_tables_summary(
            self.config.data_source_name
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT_TEMPLATE.format(
                schema_context=schema_context
            )),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        return AgentExecutor(agent=agent, tools=self.tools, verbose=True)

    async def chat(self, user_input: str) -> AgentResponse:
        """处理用户输入，返回 Agent 响应"""

    def _inject_long_term_memory(self, user_input: str) -> str:
        """从长期记忆中检索相关上下文，注入到当前对话"""
```

#### 3.3.3 SQL 确认回调

Agent 生成 SQL 后，在执行前拦截并等待用户确认。

```python
class SQLConfirmationHandler:
    """SQL 执行前的用户确认处理"""

    async def request_confirmation(self, sql: str) -> ConfirmationResult:
        """
        向用户展示 SQL 并等待确认。

        返回:
        - action: "confirm" / "modify" / "cancel"
        - modified_sql: str | None (当 action 为 "modify" 时)
        """

class ConfirmationResult(BaseModel):
    action: Literal["confirm", "modify", "cancel"]
    modified_sql: str | None = None
```

### 3.4 Tool 实现

#### 3.4.1 list_tables

```python
from langchain_core.tools import tool

@tool
def list_tables() -> str:
    """列出所有可用的数据表及其描述。
    在需要了解有哪些数据可以查询时使用此工具。
    """
    # 返回格式：
    # 1. orders - 订单主表，记录所有用户订单信息
    # 2. users - 用户表
    # ...
```

#### 3.4.2 get_schema

```python
@tool
def get_schema(table_name: str) -> str:
    """获取指定数据表的详细结构信息，包括字段名、类型、描述、枚举值等。
    在需要了解表的具体字段以生成 SQL 时使用此工具。

    Args:
        table_name: 要查询的表名
    """
    # 返回格式：
    # 表名: orders
    # 描述: 订单主表，记录所有用户订单信息
    # 字段:
    #   - id (BIGINT) [主键]: 订单ID
    #   - status (TINYINT): 订单状态 {0: 待支付, 1: 已支付, ...}
    #   ...
    # 关联关系:
    #   - orders.user_id -> users.id (多对一): 每个订单属于一个用户
```

#### 3.4.3 execute_sql

这是最关键的工具，包含安全校验和用户确认流程。

```python
@tool
def execute_sql(sql: str) -> str:
    """执行 SQL 查询并返回结果。仅支持 SELECT 查询。
    在需要从数据库获取数据时使用此工具。

    Args:
        sql: 要执行的 SQL 查询语句（仅支持 SELECT）
    """
    # 1. SQL 安全校验
    validation = sql_validator.validate(sql)
    if not validation.is_valid:
        return f"SQL 校验失败: {validation.reason}"

    # 2. 请求用户确认（通过回调）
    confirmation = await confirmation_handler.request_confirmation(sql)
    if confirmation.action == "cancel":
        return "用户已取消本次查询。"
    if confirmation.action == "modify":
        sql = confirmation.modified_sql

    # 3. 执行查询
    result = db_manager.execute_query(sql)

    # 4. 格式化返回
    return format_query_result(result)
```

#### 3.4.4 get_sample_data

```python
@tool
def get_sample_data(table_name: str, limit: int = 5) -> str:
    """获取指定表的示例数据，帮助理解数据的实际内容和格式。

    Args:
        table_name: 要查询的表名
        limit: 返回的行数，默认 5 行
    """
    sql = f"SELECT * FROM {table_name} LIMIT {limit}"
    # 执行并格式化返回
```

### 3.5 记忆系统

#### 3.5.1 对话历史（短期记忆）

```python
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

class ChatMemory:
    """管理会话级别的对话历史"""

    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self.sessions: dict[str, ChatMessageHistory] = {}

    def get_session(self, session_id: str) -> ChatMessageHistory:
        """获取或创建会话历史"""

    def save_session(self, session_id: str) -> None:
        """持久化会话历史到文件"""

    def load_session(self, session_id: str) -> ChatMessageHistory | None:
        """从文件恢复会话历史"""
```

#### 3.5.2 长期记忆（FAISS）

跨会话持久化，存储用户偏好、历史分析结论、常用查询模式。

```python
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

class LongTermMemory:
    """基于 FAISS 的长期记忆"""

    def __init__(self, persist_dir: str):
        self.persist_dir = persist_dir
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = self._load_or_create()

    def _load_or_create(self) -> FAISS:
        """加载已有的向量库，或创建新的"""

    def store(self, content: str, metadata: dict) -> None:
        """
        存储一条记忆。

        metadata 包含:
        - type: "analysis_result" / "user_preference" / "query_pattern"
        - session_id: 来源会话
        - timestamp: 时间戳
        """

    def retrieve(self, query: str, top_k: int = 5) -> list[str]:
        """根据语义相似度检索相关记忆"""

    def persist(self) -> None:
        """持久化到磁盘"""
```

**记忆存储时机**：

| 事件 | 存储内容 | 类型 |
|------|---------|------|
| SQL 查询完成 | 用户问题 + 生成的 SQL + 结果摘要 | query_pattern |
| Agent 给出分析结论 | 结论文本 | analysis_result |
| 用户表达偏好 | 偏好描述（如"我主要关注华东地区"） | user_preference |

---

## 4. 核心流程详细设计

### 4.1 完整请求处理流程

```
用户输入: "过去30天订单取消率是多少？"
  │
  ▼
┌─────────────────────────────────────────────────┐
│ 1. ChatMemory 加载对话历史                        │
│ 2. LongTermMemory 检索相关记忆                    │
│    → 找到: "用户之前分析过订单状态分布"             │
│ 3. 拼装完整上下文发送给 AgentExecutor              │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│ AgentExecutor (LLM 推理)                         │
│                                                  │
│ LLM 思考: 需要查询 orders 表的 status 字段         │
│ → 调用 get_schema("orders")                      │
│ → 获得: status 枚举 {4: "已取消"}                 │
│ → 生成 SQL:                                      │
│   SELECT                                         │
│     COUNT(CASE WHEN status=4 THEN 1 END) as ..., │
│     ...                                          │
│   FROM orders                                    │
│   WHERE created_at >= DATE_SUB(...)              │
│ → 调用 execute_sql(sql)                          │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│ execute_sql 内部流程                              │
│                                                  │
│ 1. SQLValidator 校验 → 通过（仅 SELECT）          │
│ 2. SQLConfirmationHandler 展示 SQL:               │
│    ┌──────────────────────────────────┐           │
│    │ 即将执行以下 SQL:                  │           │
│    │ SELECT COUNT(CASE WHEN status=4  │           │
│    │   THEN 1 END) AS cancelled, ...  │           │
│    │                                  │           │
│    │ [确认] [修改] [取消]              │           │
│    └──────────────────────────────────┘           │
│ 3. 用户确认 → DatabaseManager 执行                │
│ 4. 返回结果: {cancelled: 490, total: 8450, ...}   │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│ LLM 解读结果                                     │
│ → "过去30天订单取消率为 5.8%..."                   │
│                                                  │
│ 后处理:                                          │
│ 1. 存入 ChatMemory                               │
│ 2. 存入 LongTermMemory (analysis_result)         │
│ 3. 返回给用户                                     │
└─────────────────────────────────────────────────┘
```

### 4.2 Schema 上下文注入策略

Schema 信息注入 LLM 上下文有两个层次：

**层次 1：System Prompt 全局注入（表摘要）**

在 System Prompt 中注入所有表的简要描述，让 LLM 了解全局数据结构。

```
可用数据表:
1. orders - 订单主表（字段: id, user_id, total_amount, status, created_at）
2. users - 用户表（字段: id, name, region, created_at）
3. products - 商品表（字段: id, name, category, price）
```

**层次 2：Tool 调用按需获取（字段详情）**

当 LLM 需要生成 SQL 时，通过 `get_schema` 工具获取表的完整字段定义（含枚举映射、外键关系等）。

这种两层策略的好处：
- 不会在 System Prompt 中注入过多 Token（节省成本）
- LLM 能根据问题智能选择需要详细了解的表
- 枚举值映射等详细信息在需要时才获取

### 4.3 错误处理策略

| 错误场景 | 处理方式 |
|---------|---------|
| 数据库连接失败 | 返回友好提示，建议检查配置 |
| SQL 语法错误 | 捕获异常，让 LLM 基于错误信息修正 SQL 后重试（最多 2 次） |
| 查询超时 | 中断查询，提示用户优化查询条件 |
| 查询结果过大 | 自动截断（默认 500 行），提示用户添加筛选条件 |
| Schema 文件格式错误 | 启动时校验，给出明确的错误位置和修复建议 |
| LLM API 调用失败 | 重试（最多 3 次，指数退避），失败后提示用户 |

---

## 5. 配置管理

### 5.1 应用配置文件

**`config/settings.yaml`**

```yaml
app:
  name: "Data Agent"
  debug: false

llm:
  provider: openai
  model: gpt-4o
  temperature: 0
  max_tokens: 4096

database:
  max_query_rows: 500
  query_timeout: 30                   # 秒

schema:
  dir: "./schemas"                    # Schema 配置文件目录

memory:
  chat_history_max_messages: 50
  long_term_memory_dir: "./data/memory"
  long_term_memory_top_k: 5
```

### 5.2 环境变量

```bash
OPENAI_API_KEY=sk-xxx                 # OpenAI API Key（必需）
DATA_AGENT_CONFIG=./config/settings.yaml  # 配置文件路径（可选）
```

### 5.3 配置数据模型

```python
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
    llm: LLMConfig = LLMConfig()
    database: DatabaseConfig = DatabaseConfig()
    schema_dir: str = "./schemas"
    memory: MemoryConfig = MemoryConfig()
```

---

## 6. CLI 交互设计（MVP）

MVP 阶段使用命令行交互验证核心链路，基于 Rich 库实现美观的终端 UI。

### 6.1 启动流程

```bash
$ python -m data_agent --schema ./schemas/ecommerce.yaml

╭──────────────────────────────────────────╮
│          Data Agent v0.1.0               │
│   数据分析 AI 助手 · 输入问题开始分析     │
├──────────────────────────────────────────┤
│  数据源: 电商业务库 (MySQL)               │
│  已加载: 3 张表 (orders, users, products) │
│  输入 /help 查看帮助                      │
╰──────────────────────────────────────────╯

You >
```

### 6.2 交互示例

```
You > 过去30天的订单取消率是多少？

Agent > 让我查询一下订单数据。

┌─ 生成的 SQL ──────────────────────────────────┐
│ SELECT                                         │
│   COUNT(CASE WHEN status = 4 THEN 1 END)       │
│     AS cancelled,                              │
│   COUNT(*) AS total,                           │
│   ROUND(COUNT(CASE WHEN status = 4 THEN 1 END) │
│     / COUNT(*) * 100, 2) AS cancel_rate        │
│ FROM orders                                    │
│ WHERE created_at >= DATE_SUB(CURDATE(),         │
│   INTERVAL 30 DAY);                            │
└────────────────────────────────────────────────┘
确认执行？ [Y]确认  [E]编辑  [N]取消: Y

✓ 查询完成 (0.23s, 1 行)

过去30天订单取消率为 5.8%（490 笔取消 / 8,450 笔总订单）。
相比上月（4.2%）有所上升，建议关注取消原因。

You >
```

### 6.3 CLI 命令

| 命令 | 描述 |
|------|------|
| `/help` | 显示帮助信息 |
| `/tables` | 列出所有可用表 |
| `/schema <表名>` | 查看表的详细结构 |
| `/history` | 查看对话历史 |
| `/clear` | 清除当前对话上下文 |
| `/exit` | 退出程序 |

---

## 7. 依赖清单

```
# requirements.txt

# LLM
langchain>=0.3
langchain-openai>=0.3
langchain-community>=0.3

# Database
sqlalchemy>=2.0
pymysql                          # MySQL 驱动
psycopg2-binary                  # PostgreSQL 驱动

# Vector Store
faiss-cpu
langchain-community              # FAISS integration

# Data Processing
pandas

# Configuration
pydantic>=2.0
pydantic-settings
pyyaml

# CLI
rich
prompt-toolkit

# Utilities
python-dotenv
```

---

## 8. 开发计划

基于模块依赖关系，按以下顺序逐步实现：

### Phase 1：基础骨架

| 任务 | 产出 |
|------|------|
| 项目初始化 | 目录结构、`pyproject.toml`、依赖安装 |
| 配置管理 | `settings.py`、YAML 配置加载、环境变量 |
| Schema 加载 | `SchemaLoader`、Pydantic 模型、示例 Schema |

### Phase 2：核心链路

| 任务 | 产出 |
|------|------|
| 数据库访问层 | `DatabaseManager`、连接池、查询执行 |
| SQL 安全校验 | `SQLValidator`、关键词拦截 |
| Agent Tool 实现 | 4 个工具：`list_tables`、`get_schema`、`execute_sql`、`get_sample_data` |
| Agent 构建 | `DataAgent`、System Prompt、AgentExecutor |
| SQL 确认流程 | `SQLConfirmationHandler` |

### Phase 3：交互与记忆

| 任务 | 产出 |
|------|------|
| CLI 交互界面 | Rich 终端 UI、命令解析 |
| 对话历史 | `ChatMemory`、会话持久化 |
| 长期记忆 | `LongTermMemory`、FAISS 存储与检索 |

### Phase 4：端到端验证

| 任务 | 产出 |
|------|------|
| 示例数据库 | SQLite 测试数据库 + 示例数据 |
| 端到端测试 | 完整链路跑通：提问 → SQL → 确认 → 执行 → 解读 |
| 文档 | README、使用说明 |

---

## 9. 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| LLM 生成的 SQL 不准确 | 查询结果错误或执行报错 | SQL 安全校验 + 用户确认兜底；错误后自动重试修正 |
| Schema 过大超出上下文窗口 | LLM 无法处理全部表信息 | 两层注入策略（摘要 + 按需获取） |
| 数据库查询性能差 | 用户等待时间过长 | 查询超时限制；提示用户优化条件 |
| OpenAI API 不稳定 | 服务中断 | 重试机制；后续可扩展多 LLM 后端 |
| FAISS 记忆检索不精准 | 长期记忆引入噪音 | 设置相似度阈值；定期清理低质量记忆 |
