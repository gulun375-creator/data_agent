# Data Agent

基于大语言模型的数据分析 AI Agent，支持用户通过自然语言问答完成数据分析。

## 核心特性

- **Schema 驱动**：通过 YAML/JSON 配置文件定义数据表结构，Agent 基于 Schema 理解数据
- **自然语言转 SQL**：用户用中文提问，Agent 自动生成并执行 SQL 查询
- **安全机制**：SQL 安全校验 + 执行前用户确认
- **多轮对话**：支持上下文关联的连续分析
- **长期记忆**：跨会话记忆用户偏好和历史分析结论（FAISS）

## 技术栈

Python / LangChain / OpenAI GPT / SQLAlchemy / FAISS / Rich

## 快速开始

### 1. 安装

```bash
pip install -e .
```

### 2. 配置

复制环境变量模板并填入 OpenAI API Key：

```bash
cp .env.example .env
# 编辑 .env，填入 OPENAI_API_KEY
```

### 3. 初始化示例数据库

```bash
python3 scripts/init_example_db.py
```

### 4. 运行

```bash
python3 -m data_agent
```

## 项目结构

```
data_agent/
├── main.py                  # 应用入口
├── config/
│   ├── settings.py          # 全局配置
│   └── schema_loader.py     # Schema 配置加载与校验
├── agent/
│   ├── agent.py             # Agent 核心（LangChain AgentExecutor）
│   └── prompts.py           # System Prompt 模板
├── tools/
│   ├── list_tables.py       # 列出所有表
│   ├── get_schema.py        # 获取表结构详情
│   ├── execute_sql.py       # 执行 SQL 查询
│   └── get_sample_data.py   # 获取示例数据
├── database/
│   ├── connection.py        # 数据库连接管理
│   └── sql_validator.py     # SQL 安全校验
├── memory/
│   ├── chat_memory.py       # 对话历史
│   └── long_term_memory.py  # 长期记忆（FAISS）
└── cli/
    └── app.py               # CLI 交互界面

schemas/                     # Schema 配置文件
config/                      # 应用配置
scripts/                     # 工具脚本
docs/                        # 文档
```

## CLI 命令

| 命令 | 描述 |
|------|------|
| `/help` | 显示帮助 |
| `/tables` | 列出所有可用表 |
| `/schema <表名>` | 查看表结构详情 |
| `/history` | 查看对话历史 |
| `/clear` | 清除对话上下文 |
| `/exit` | 退出 |

## 文档

- [需求文档](docs/requirements.md)
- [技术方案](docs/technical-design.md)
