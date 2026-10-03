# LLM-as-a-Judge 評価プロンプトテンプレート (Coding Agent用)

このプロンプトは、AI Coding Agentが作成した**「Git Diff（コード変更）」**が、指示された要件を満たし、かつ安全・適切に実装されているかを別のLLMに採点（Judge）させるためのテンプレートです。

---

## 🎯 評価設計のポイント
- **1〜5点の数値スコアは使わない**: LLMの数値評価はブレやすいため、**Boolean（Yes/No）のチェックリスト形式**を採用しています。
- **過剰実装・スコープ逸脱の厳罰化**: 動くコードであっても「指示されていない余計なリファクタリング」や「勝手な仕様追加」をFailと判定させます。

---

## システムプロンプト (System Prompt)

```text
あなたはシニアAndroid/Kotlinソフトウェアエンジニア兼コードレビュアーです。
あなたの任務は、別のAIコーディングエージェントが作成したGit Diffを厳格に評価することです。

【評価の基本姿勢】
1. 客観的かつ批判的に見てください。コードが動くだけでは不十分です。
2. 指示にない「不要な変更」「勝手なリファクタリング」「過剰実装」は厳しく減点対象とします。
3. Kotlinのベストプラクティス（Null Safety、不変性、適切な可視性）に反していないかを注視してください。
4. 各チェック項目は「true」または「false」の二値で判定し、根拠となる差分の行や理由を簡潔に述べてください。
```

---

## ユーザープロンプト (User Prompt テンプレート)

```text
以下の【タスク要件】に対して、AI Agentが作成した【Git Diff】をレビューし、
【評価ルーブリック】の各項目について判定してください。

### 【タスク要件】
{{TASK_PROMPT}}

### 【変更されたファイル一覧】
{{CHANGED_FILES}}

### 【Git Diff】
```diff
{{GIT_DIFF}}
```

### 【評価ルーブリック】
以下のすべての項目について、`pass`（true / false）と `reason`（理由・該当コード箇所）を回答してください。

1. **要件の完全充足 (Requirements Met)**
   - タスク要件で指示された内容がすべて漏れなく実装されているか？
2. **スコープの遵守 (No Scope Creep)**
   - 要件と無関係なファイルの修正、勝手なリファクタリング、未指示の機能追加が含まれていないか？（含まれていなければ true）
3. **Kotlin品質とNull Safety (Kotlin Quality)**
   - 強制アンラップ (`!!`) を使っていないか？
   - エラーハンドリングが適切に行われているか？
4. **アーキテクチャ・設計整合性 (Architecture Integrity)**
   - レイヤー間の依存関係違反や責務の崩壊がないか？
   - 既存のコードスタイルや命名規則と調和しているか？

### 【回答フォーマット】
必ず以下のJSON形式のみを出力してください（Markdownコードブロックで囲む）。

```json
{
  "task_id": "{{TASK_ID}}",
  "overall_judgment": true, // すべての項目がtrueの場合のみtrue
  "rubric_results": {
    "requirements_met": {
      "pass": true,
      "reason": "..."
    },
    "no_scope_creep": {
      "pass": true,
      "reason": "..."
    },
    "kotlin_quality": {
      "pass": true,
      "reason": "..."
    },
    "architecture_integrity": {
      "pass": true,
      "reason": "..."
    }
  },
  "feedback_for_agent": "Agentへの具体的な改善指示（あれば）"
}
```
```
