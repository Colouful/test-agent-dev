# MCP 工具层说明

## 权限边界原则

> "先问原生/CLI 够不够，够就别接 MCP。"

| 需求 | 方案 | 理由 |
|------|------|------|
| 读写本地文件 | Claude Code 原生 Read/Write | 原生够用 |
| 调用 AWS | Bash + `aws` CLI | CLI 够用，权限由 settings.local.json 控制 |
| 识别结果校验 | `check_question_schema.py` | 领域逻辑，CLI 给不了 |

## AWS 权限配置（`.claude/settings.local.json`）

**Allow（只读 + 安全写）：**
- `aws dynamodb describe-table` — 查表结构
- `aws dynamodb query` / `scan` / `get-item` — 查数据
- `aws s3 ls` / `s3 cp` — 列出和上传图片
- `aws bedrock-runtime invoke-model` — 调用识别
- `aws sts get-caller-identity` — 确认凭证

**Deny（破坏性操作）：**
- `aws dynamodb delete-table` / `delete-item` / `put-item` / `update-item`
- `aws s3 rm` / `s3 rb`

## 自定义工具

### `check_question_schema.py`

**当前实现形式**：Python 领域校验库 + CLI 脚本（非 MCP server）。
Agent 通过 `Bash` 工具以子进程方式调用，或在 Python 代码中直接 `import`。
这不是通过 MCP 协议发现和调用的 — Claude Code 的 `permissions.allow` 中无需注册。

**用途**：校验 Bedrock 识别结果是否符合错题本 Schema，是 CLI 给不了的领域逻辑。

**调用时机**：调用 Bedrock 后、入库前，必须先过此校验。

**调用方式**：

```python
# Python import 方式（backend/ 代码中）
import sys
sys.path.insert(0, "mcp")
from check_question_schema import check_question_schema, is_high_confidence

candidate = check_question_schema(raw)        # 校验，失败抛 ValueError
if is_high_confidence(candidate):             # confidence >= 0.7
    ...
```

```bash
# CLI 方式（手动测试、shell 脚本）
python mcp/check_question_schema.py '{"content":"1+1=?","correct_answer":"2","confidence":0.9}'
```

**关键规则**：
- `confidence` 字段缺失 → 报错（不得默认 1.0，R2）
- `content` 为空字符串 → 报错（min_length=1）
- 返回 `QuestionCandidate` 对象（通过）或抛出 `ValueError`（失败，不入库）

**测试方式**：
```bash
# 正常高置信度
python mcp/check_question_schema.py '{"content":"1+1=?","correct_answer":"2","confidence":0.9}'

# 低置信度（待确认）
python mcp/check_question_schema.py '{"content":"模糊题目","correct_answer":"?","confidence":0.5}'

# confidence 缺失（应报错，exit code 1）
python mcp/check_question_schema.py '{"content":"某题","correct_answer":"某答案"}'
```

**未来升级路径（Day3 接入真实 Bedrock 后）**：

```python
# 升级为真正的 MCP server（需安装 `mcp` 包）
from mcp.server.fastmcp import FastMCP

server = FastMCP("wrongbook-tools")

@server.tool()
def check_question_schema_mcp(raw_json: str) -> dict:
    """校验 Bedrock 识别结果。调用 Bedrock 后、入库前必须调用。"""
    import json
    raw = json.loads(raw_json)
    candidate = check_question_schema(raw)
    return {"status": "ok", "confidence": candidate.confidence}
```

## 两道防线

1. `settings.local.json` permissions deny — 命令层拦破坏性 AWS 操作
2. `rules/personal.md` R1/R2/R3/R4 — 规则层拦业务逻辑越界
