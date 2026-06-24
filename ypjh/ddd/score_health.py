#!/usr/bin/env python3
"""
DDD 架构健康体检 — 检查项目是否遵循分层架构约束。

检查维度：
  L1 路由层：不得直接 import Repository 或 Model（只能调 Service）
  L2 Service 层：不得直接 import FastAPI Request/Response
  L3 Repository 层：不得包含业务逻辑（if confidence、status 判断）
  L4 规则合规：R1 user_id 隔离 / R3 禁止裸字符串

退出码：0=全部通过，1=有问题，2=无 backend 目录（跳过）
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

BACKEND = Path(__file__).parent.parent / "backend"

# ── 判据 ───────────────────────────────────────────────────────────────────────

ROUTER_FORBIDDEN_IMPORTS = {
    "repositories",   # 路由层不得直接调 repo
    "models",         # 路由层不得直接用 ORM model
}

SERVICE_FORBIDDEN_IMPORTS = {
    "fastapi",        # service 层不得直接依赖 HTTP 层
    "starlette",
}

REPO_BUSINESS_PATTERNS = [
    "confidence",     # 业务决策不该出现在 repo 里
    "pending_review",
    "high_confidence",
]

RAW_STRING_PATTERNS = [
    "raw_text",
    "raw_content",
]


# ── 数据结构 ───────────────────────────────────────────────────────────────────

@dataclass
class Issue:
    level: str        # ERROR / WARN
    rule: str
    file: str
    line: int
    detail: str


@dataclass
class HealthReport:
    issues: list[Issue] = field(default_factory=list)

    def add(self, level: str, rule: str, file: str, line: int, detail: str) -> None:
        self.issues.append(Issue(level, rule, file, line, detail))

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "ERROR"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "WARN"]

    def score(self) -> int:
        """100 - 10*errors - 3*warnings，最低 0。"""
        return max(0, 100 - 10 * len(self.errors) - 3 * len(self.warnings))


# ── 检查函数 ───────────────────────────────────────────────────────────────────

def _imports_of(source: str) -> list[tuple[int, str]]:
    """返回 [(lineno, module_name), ...]。"""
    result: list[tuple[int, str]] = []
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return result
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                result.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                result.append((node.lineno, node.module))
    return result


def check_router_layer(report: HealthReport) -> None:
    endpoints_dir = BACKEND / "api"
    if not endpoints_dir.exists():
        return
    for py_file in endpoints_dir.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        for lineno, module in _imports_of(source):
            for forbidden in ROUTER_FORBIDDEN_IMPORTS:
                if forbidden in module:
                    report.add(
                        "ERROR", "L1-ROUTER-DIRECT-DB",
                        str(py_file.relative_to(BACKEND.parent)), lineno,
                        f"路由层直接 import '{module}'（应通过 Service 层）",
                    )


def check_service_layer(report: HealthReport) -> None:
    services_dir = BACKEND / "services"
    if not services_dir.exists():
        return
    for py_file in services_dir.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        for lineno, module in _imports_of(source):
            for forbidden in SERVICE_FORBIDDEN_IMPORTS:
                if module.startswith(forbidden):
                    report.add(
                        "WARN", "L2-SERVICE-HTTP-LEAK",
                        str(py_file.relative_to(BACKEND.parent)), lineno,
                        f"Service 层 import HTTP 框架 '{module}'",
                    )


def check_repo_layer(report: HealthReport) -> None:
    repos_dir = BACKEND / "repositories"
    if not repos_dir.exists():
        return
    for py_file in repos_dir.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), 1):
            for pattern in REPO_BUSINESS_PATTERNS:
                if pattern in line and not line.strip().startswith("#"):
                    report.add(
                        "WARN", "L3-REPO-BUSINESS-LOGIC",
                        str(py_file.relative_to(BACKEND.parent)), lineno,
                        f"Repository 层含业务关键字 '{pattern}'（应在 Service 层处理）",
                    )


def check_raw_string(report: HealthReport) -> None:
    for py_file in BACKEND.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(source.splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            for pattern in RAW_STRING_PATTERNS:
                if pattern in line:
                    report.add(
                        "ERROR", "R3-RAW-STRING",
                        str(py_file.relative_to(BACKEND.parent)), lineno,
                        f"禁止裸字符串字段 '{pattern}'（违反 R3）",
                    )


def check_user_id_isolation(report: HealthReport) -> None:
    """粗检：Repository 方法里没有 user_id 参数的查询函数。"""
    repos_dir = BACKEND / "repositories"
    if not repos_dir.exists():
        return
    for py_file in repos_dir.rglob("*.py"):
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = node.name.lower()
            # 只检查查询类函数
            if not any(kw in name for kw in ("get", "find", "list", "query", "fetch")):
                continue
            args = [a.arg for a in node.args.args]
            if "user_id" not in args and "current_user" not in args:
                report.add(
                    "WARN", "R1-MISSING-USER-ISOLATION",
                    str(py_file.relative_to(BACKEND.parent)), node.lineno,
                    f"函数 '{node.name}' 无 user_id 参数，可能违反 R1 隔离约束",
                )


# ── 主函数 ─────────────────────────────────────────────────────────────────────

def main() -> int:
    if not BACKEND.exists():
        print("ARCH_SKIP — 未找到 backend/ 目录")
        return 2

    report = HealthReport()
    check_router_layer(report)
    check_service_layer(report)
    check_repo_layer(report)
    check_raw_string(report)
    check_user_id_isolation(report)

    score = report.score()
    errors = len(report.errors)
    warnings = len(report.warnings)

    print(f"DDD 健康分：{score}/100  （{errors} 错误，{warnings} 警告）")
    print("=" * 60)

    if not report.issues:
        print("全部通过，架构健康！")
        return 0

    for issue in sorted(report.issues, key=lambda i: (i.level, i.file, i.line)):
        tag = "[ERROR]" if issue.level == "ERROR" else "[ WARN]"
        print(f"{tag} {issue.rule}")
        print(f"       {issue.file}:{issue.line}")
        print(f"       {issue.detail}")
        print()

    if errors > 0:
        print(f"ARCH_FAIL — {errors} 个错误需修复")
        return 1

    print(f"ARCH_WARN — {warnings} 个警告，建议改善")
    return 0


if __name__ == "__main__":
    sys.exit(main())
