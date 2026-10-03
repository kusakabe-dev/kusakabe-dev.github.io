#!/usr/bin/env python3
"""
check_agent_diff.py - Coding Agent Diff Grader for Kotlin / Android Projects

Coding Agentが生成したコード差分（git diff）を解析し、
安全基準・スコープ逸脱・Kotlinアンチパターンを決定論的（Deterministic）に判定する評価スクリプト。

外部依存ライブラリなし（Python 3.8+ 標準ライブラリのみ）で動作します。

【主なチェック項目】
1. Kotlin強制アンラップ (`!!`) の追加検知
2. 変更ファイル数の上限超過（スコープ逸脱の抑止）
3. 変更行数の上限超過
4. 保護対象ファイル（build.gradle.kts, libs.versions.toml 等）の無断改変検知
5. デバッグコード（println, Log.d, TODO）の混入警告

【使用例】
  # ワーキングツリーの変更をチェック
  python3 check_agent_diff.py

  # 直前のコミット（Agentの作成したコミット）をチェック
  python3 check_agent_diff.py --diff-target HEAD~1

  # CIやEvalパイプライン向けにJSON形式で結果出力
  python3 check_agent_diff.py --json
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple


# デフォルトの保護対象ファイル（Agentが無断で触るべきではない基盤ファイル）
DEFAULT_PROTECTED_PATTERNS = [
    r"^settings\.gradle(\.kts)?$",
    r"^gradle/libs\.versions\.toml$",
    r"^\.github/workflows/",
    r".*\.keystore$",
    r".*\.jks$",
    r"^gradlew(\.bat)?$",
]

# デフォルトの警告パターン（追加行に存在した場合にフラグを立てる）
DEFAULT_WARNING_PATTERNS = [
    (r"\bprintln\s*\(", "println() が残っています"),
    (r"\bLog\.[vd]\s*\(", "詳細ログ (Log.v / Log.d) が残っています"),
    (r"\bTODO\b", "未実装の TODO コメントが追加されています"),
    (r"\bFIXME\b", "FIXME コメントが追加されています"),
]


def get_git_diff(target: str, cwd: Optional[str] = None) -> Tuple[str, List[str]]:
    """git diff の内容と変更ファイル一覧を取得する"""
    try:
        # 変更ファイル一覧
        if target == "working-tree":
            files_cmd = ["git", "diff", "--name-only", "HEAD"]
            diff_cmd = ["git", "diff", "HEAD"]
        elif "..." in target or ".." in target:
            files_cmd = ["git", "diff", "--name-only", target]
            diff_cmd = ["git", "diff", target]
        else:
            files_cmd = ["git", "diff", "--name-only", f"{target}..HEAD"]
            diff_cmd = ["git", "diff", f"{target}..HEAD"]

        files_output = subprocess.check_output(files_cmd, cwd=cwd, text=True, stderr=subprocess.PIPE)
        diff_output = subprocess.check_output(diff_cmd, cwd=cwd, text=True, stderr=subprocess.PIPE)

        changed_files = [line.strip() for line in files_output.splitlines() if line.strip()]
        return diff_output, changed_files
    except subprocess.CalledProcessError as e:
        print(f"Error running git command: {e.stderr}", file=sys.stderr)
        sys.exit(2)


def evaluate_diff(
    diff_text: str,
    changed_files: List[str],
    max_files: int,
    max_lines: int,
    protected_patterns: List[str],
    allow_double_bang: bool,
) -> Dict:
    """差分を解析してスコアと違反内容をまとめる"""
    violations = []
    warnings = []
    added_lines_count = 0
    deleted_lines_count = 0
    double_bang_occurrences = []

    # 1. 変更ファイル数のチェック
    file_count = len(changed_files)
    if file_count > max_files:
        violations.append(
            f"変更ファイル数が上限({max_files})を超えています: {file_count} files"
        )

    # 2. 保護対象ファイルのチェック
    for f in changed_files:
        for pattern in protected_patterns:
            if re.search(pattern, f):
                violations.append(f"保護対象ファイルが変更されています: {f} (pattern: {pattern})")

    # 3. 差分の行単位解析
    current_file = None
    line_number = 0

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            line_number = 0
            continue
        elif line.startswith("@@"):
            # hunk header (e.g., @@ -10,5 +12,8 @@)
            match = re.search(r"\+(\d+)", line)
            if match:
                line_number = int(match.group(1))
            continue

        if line.startswith("+") and not line.startswith("+++"):
            added_lines_count += 1
            code_content = line[1:]

            # Kotlinファイルの場合のチェック
            if current_file and (current_file.endswith(".kt") or current_file.endswith(".kts")):
                # !! の検知
                if not allow_double_bang and "!!" in code_content:
                    # コメント行を除外する簡易チェック
                    stripped = code_content.strip()
                    if not stripped.startswith("//") and not stripped.startswith("*"):
                        double_bang_occurrences.append(
                            f"{current_file}:{line_number} -> {code_content.strip()}"
                        )

            # 警告パターンの検知
            for pat, desc in DEFAULT_WARNING_PATTERNS:
                if re.search(pat, code_content):
                    warnings.append(f"{current_file}:{line_number} -> {desc}: {code_content.strip()}")

            line_number += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted_lines_count += 1
        elif not line.startswith("-") and not line.startswith("---"):
            line_number += 1

    if double_bang_occurrences:
        violations.append(
            f"Kotlinの強制アンラップ ('!!') が追加されています ({len(double_bang_occurrences)}箇所):\n  "
            + "\n  ".join(double_bang_occurrences[:5])
            + (f"\n  ...他 {len(double_bang_occurrences)-5} 件" if len(double_bang_occurrences) > 5 else "")
        )

    # 4. 総変更行数チェック
    total_changed_lines = added_lines_count + deleted_lines_count
    if total_changed_lines > max_lines:
        violations.append(
            f"総変更行数が上限({max_lines}行)を超えています: +{added_lines_count}/-{deleted_lines_count} (合計 {total_changed_lines}行)"
        )

    passed = len(violations) == 0

    return {
        "passed": passed,
        "metrics": {
            "changed_files_count": file_count,
            "added_lines": added_lines_count,
            "deleted_lines": deleted_lines_count,
            "total_changed_lines": total_changed_lines,
            "double_bang_count": len(double_bang_occurrences),
        },
        "changed_files": changed_files,
        "violations": violations,
        "warnings": warnings,
    }


def main():
    parser = argparse.ArgumentParser(description="Coding Agent Diff Grader for Android / Kotlin")
    parser.add_argument(
        "--diff-target",
        default="working-tree",
        help="diff対象（'working-tree', 'HEAD~1', 'main...HEAD' など。デフォルト: working-tree）",
    )
    parser.add_argument("--max-files", type=int, default=10, help="許容する最大変更ファイル数（デフォルト: 10）")
    parser.add_argument("--max-lines", type=int, default=400, help="許容する最大変更行数（デフォルト: 400）")
    parser.add_argument(
        "--allow-double-bang",
        action="store_true",
        help="Kotlinの '!!' 演算子の追加を許容する場合は指定",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="警告 (println/TODO等) がある場合も不合格 (Exit 1) とする",
    )
    parser.add_argument("--json", action="store_true", help="結果をJSON形式で標準出力する")

    args = parser.parse_args()

    diff_text, changed_files = get_git_diff(args.diff_target)
    result = evaluate_diff(
        diff_text=diff_text,
        changed_files=changed_files,
        max_files=args.max_files,
        max_lines=args.max_lines,
        protected_patterns=DEFAULT_PROTECTED_PATTERNS,
        allow_double_bang=args.allow_double_bang,
    )

    if args.strict and result["warnings"]:
        result["passed"] = False
        result["violations"].append(f"--strict指定: 警告が {len(result['warnings'])} 件存在するため不合格")

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("========================================")
        print(" Agent Diff Evaluation Report")
        print("========================================")
        status_str = "\033[32m[PASSED]\033[0m" if result["passed"] else "\033[31m[FAILED]\033[0m"
        print(f"Overall Result: {status_str}\n")
        print(f"Files Changed : {result['metrics']['changed_files_count']} (Max: {args.max_files})")
        print(f"Lines Changed : +{result['metrics']['added_lines']} / -{result['metrics']['deleted_lines']} (Total: {result['metrics']['total_changed_lines']}, Max: {args.max_lines})")
        print(f"Null Assert(!!): {result['metrics']['double_bang_count']}")
        print("----------------------------------------")

        if result["violations"]:
            print("\033[31mViolations (Must Fix):\033[0m")
            for v in result["violations"]:
                print(f"  ❌ {v}")
            print()

        if result["warnings"]:
            print("\033[33mWarnings (Review Recommended):\033[0m")
            for w in result["warnings"]:
                print(f"  ⚠️  {w}")
            print()

        if result["passed"] and not result["warnings"]:
            print("✨ すべての安全性・スコープ基準を満たしています。")

    sys.exit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
