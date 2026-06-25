# 项目持久记忆

## Key Decisions
- [2026-06-25] **使用 JWT 认证** — 无状态、前后端分离适配好
- [2026-06-25] **SQLite(dev) / DynamoDB(prod)** — Repository 抽象隔离，切换零成本
- [2026-06-25] **低置信度展示给用户确认，不直接入库** — 数据准确 > 操作便捷
- [2026-06-25] **验证用 mock 不验具体文字** — AI 输出非确定性，验结构和契约

## Lessons Learned
- [2026-06-25] **empty mock 不能不填 content/answer** — schema min_length=1 报错，应在 service 层用占位符降级（R9）
- [2026-06-25] **confidence 缺失不能默认 1.0** — 违反 R2，会让垃圾数据入库；强制 0.0 触发 pending_review
- [2026-06-25] **.venv 目录会被 arch-check 误扫** — grep 模式需排除第三方包路径

## Recurring Patterns
- [2026-06-25] **user_id 参数遗漏** — 出现 3 次（repository/service/test），所有 DB 查询必须带 user_id
