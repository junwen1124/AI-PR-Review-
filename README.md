# AI PR Review 助手

基于大模型的 GitHub Pull Request 自动代码评审工具。输入一个 PR 链接，自动输出**变更总结**、**风险代码识别**和**Review 建议**。

## 功能特性

- **PR 变更总结**：自动分析 PR 改动了哪些文件、主要变更内容
- **风险代码识别**：识别潜在 bug、安全漏洞、性能问题、错误处理缺失等，按严重程度分级（🔴 Critical / 🟡 Medium / 🟢 Low）
- **Review 建议生成**：给出具体可操作的修改建议，覆盖代码风格、逻辑优化、命名、测试等方面

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/<your-username>/aipr.git
cd aipr
```

### 2. 创建虚拟环境并安装依赖

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置 API 密钥

复制 `.env.example` 为 `.env` 并填入真实密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# GitHub Personal Access Token（必填）
# 创建地址：https://github.com/settings/tokens
# 权限：repo（私有仓库）或 public_repo（公共仓库）
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx

# AI API Key（选择一种）
# 推荐 DeepSeek，便宜且代码能力出色
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 或者使用 OpenAI
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 可选：自定义模型和 API 地址
# AI_MODEL=deepseek-chat
# AI_BASE_URL=https://api.deepseek.com/v1
```

### 4. 运行

```bash
# 基本用法
python review.py --pr https://github.com/owner/repo/pull/123

# 保存结果到文件
python review.py --pr https://github.com/owner/repo/pull/123 --output review.md

# 指定模型
python review.py --pr https://github.com/owner/repo/pull/123 --model gpt-4o

# 禁用彩色输出（适合管道/文件）
python review.py --pr https://github.com/owner/repo/pull/123 --no-color

# 查看所有参数
python review.py --help
```

## 运行示例

```bash
$ python review.py --pr https://github.com/tensorflow/tensorflow/pull/12345

=======================================================
  AI PR Review Assistant
=======================================================
  PR: https://github.com/tensorflow/tensorflow/pull/12345
  Model: deepseek-chat

[1/3] Fetching PR from GitHub...
  Title: Fix memory leak in data loader
  Author: contributor
  Files: 3 (+45 -12)

[2/3] Building review prompt...
[3/3] Sending to AI model for review...

────────────────── Summary ──────────────────
Overview: This PR fixes a memory leak in the data loader by properly
closing file handles after reading. Affects 3 files with 45 additions
and 12 deletions.

Key Changes:
  • Added try/finally block to ensure file closure
  • Refactored buffer management in data_loader.py
  • Updated unit tests for edge cases

────────────────── Risk Identification ─────
1. [🔴 Critical] bug - src/data_loader.py
   File handle not closed on exception path (line 142)
   Fix: Wrap in context manager or try/finally

2. [🟡 Medium] performance - src/buffer.py
   Repeated list allocation in hot loop may cause GC pressure
   Fix: Pre-allocate buffer with known capacity

────────────────── Review Suggestions ───────
1. [style] src/data_loader.py
   Variable naming inconsistent with project convention
   Suggestion: Rename 'fd' to 'file_desc' for clarity

2. [testing] tests/test_loader.py
   Missing test for concurrent file access scenario
   Suggestion: Add test with threading to verify thread safety
```

## 依赖清单

| 库 | 版本 | 用途 | 许可证 |
|---|---|---|---|
| [PyGithub](https://github.com/PyGithub/PyGithub) | >=2.1.1 | GitHub API 封装，获取 PR 详情与 diff | LGPL-3.0 |
| [openai](https://github.com/openai/openai-python) | >=1.0.0 | LLM API 调用（兼容 DeepSeek/OpenAI 等） | Apache-2.0 |
| [rich](https://github.com/Textualize/rich) | >=13.0.0 | 终端彩色输出与格式化 | MIT |
| [python-dotenv](https://github.com/theskumar/python-dotenv) | >=1.0.0 | 加载 .env 环境变量配置 | BSD-3-Clause |

### 原创部分说明

本项目的原创代码包括：

- **PR 上下文获取逻辑**（`src/github_client.py`）：基于 PyGithub 封装了 PR URL 解析、完整 diff 拼接、文件变更列表提取等功能
- **结构化的 Review Prompt 设计**（`src/reviewer.py`）：设计了专用的 system prompt 和结构化的 JSON 输出格式，引导模型按照「总结 → 风险 → 建议」的三段式结构输出
- **评审结果格式化引擎**（`src/formatter.py`）：基于 Rich 库实现了 CLI 友好的彩色输出，包括风险等级的视觉区分
- **CLI 接口设计**（`src/main.py`）：完整的命令行参数体系和环境检查逻辑

第三方库 PyGithub 负责 GitHub REST API 的底层调用，openai 负责 LLM API 的 HTTP 通信，rich 提供终端渲染能力。

## 设计思路

### 1. 模型选择

**选择 DeepSeek-Chat（DeepSeek-V3）作为默认模型**，理由如下：

- **性价比**：DeepSeek 的 API 定价约为 GPT-4o 的 1/10，对于需要处理大量 diff 文本的代码评审场景，成本可控
- **代码理解能力**：DeepSeek-V3 在 HumanEval、MBPP 等代码基准测试中表现优异，能够准确理解 Python/JavaScript/Go 等多语言代码
- **上下文窗口**：支持 64K token 上下文，可以容纳较大的 PR diff
- **兼容性**：DeepSeek API 完全兼容 OpenAI SDK，便于后续切换到其他模型

同时，本工具通过 OpenAI 兼容接口设计，支持零配置切换到 GPT-4o、Claude、Qwen 等任意兼容模型，只需修改 `AI_BASE_URL` 和 `AI_MODEL` 环境变量。

### 2. 上下文获取方式

**当前策略：获取 PR 完整 diff + 文件元信息**，具体包括：

- **PR 元数据**：标题、描述、作者、分支信息、commit 数量
- **文件变更列表**：每个文件的路径、状态（added/modified/removed）、增删行数统计
- **完整 unified diff**：每个变更文件的具体代码差异（patch 内容）

**为什么不获取周边代码（文件完整内容）？**

对于大多数 PR，diff 本身已经提供了足够的上下文来理解变更。如果获取完整文件内容，会显著增加 token 消耗（一个几百行的文件远大于其 diff），却不一定提升评审质量。此外，diff 格式本身已经包含了变更前后的代码行，模型可以据此推断上下文。

**TODO 改进方向**：对于 diff 中引用了未变更函数/变量的情况，可以额外获取被引用符号所在文件的片段（通过 GitHub Contents API），实现"按需上下文扩展"。

### 3. Prompt 工程

采用**结构化 JSON 输出**的设计：

- **System Prompt**：定义专家角色、评审标准、输出格式约束
- **User Prompt**：包含 PR 元数据 + 文件列表 + 完整 diff
- **输出格式**：JSON 三段式结构（summary / risks / suggestions）

关键设计点：
- **风险分级**：使用 🔴 Critical / 🟡 Medium / 🟢 Low 三级，让评审结果一目了然
- **分类标注**：每个风险标注类型（security / bug / performance / error-handling / race-condition），便于后续统计和过滤
- **具体可操作**：要求模型给出具体文件和代码行的修复建议，而非泛泛而谈
- **Diff 截断**：默认截断 15000 字符，通过 `--max-diff-length` 可调整，平衡上下文完整性和 token 消耗

### 4. 误报与漏报控制

- **温度参数**：设置 temperature=0.3，在创造性和准确性之间取得平衡，降低模型随意发挥导致误报的概率
- **空结果允许**：prompt 明确要求"如果未发现风险，返回空数组"，避免模型强行编造问题
- **结构化输出**：JSON 格式要求模型给出具体文件和行号，不给出泛泛描述，迫使模型基于实际代码做判断

### 5. 未来扩展方向

- **增量审查**：对比连续 PR 的 diff，只审查新增变更部分，避免重复评审已审代码
- **自定义规则引擎**：支持用户在 `.aipr-rules.yml` 中定义团队编码规范（如禁止使用特定 API、命名约定检查等），结合模型评审和规则检查
- **Review 历史与趋势分析**：记录每次评审结果，生成项目代码质量趋势图
- **跨文件影响分析**：通过静态分析（AST）追踪变更的函数/类在项目中被哪些文件引用，评估变更影响范围
- **多模型投票**：同时调用多个模型进行评审，取"共识"结果以降低单一模型的偏差
- **CI/CD 集成**：提供 GitHub Actions / GitLab CI 模板，在 PR 创建时自动触发评审并评论到 PR 页面
- **多语言支持**：针对 Java、Rust、Go 等语言优化 prompt，提供语言特定的审查规则
- **交互式 Review**：支持在终端中逐条确认/驳回风险项，生成 Review 摘要评论

## 项目结构

```
aipr/
├── .env.example          # 环境变量模板
├── .gitignore
├── README.md
├── requirements.txt       # Python 依赖
├── review.py              # 根目录便捷入口
└── src/
    ├── __init__.py
    ├── __main__.py        # python -m src 入口
    ├── main.py            # CLI 入口（argparse）
    ├── github_client.py   # GitHub API 封装
    ├── ai_client.py       # LLM API 封装
    ├── reviewer.py        # Prompt 构建
    └── formatter.py       # 输出格式化
```

## License

MIT
