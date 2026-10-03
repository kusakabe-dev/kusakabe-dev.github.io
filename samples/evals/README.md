# Coding Agent Evaluation ツール＆テンプレート集

このディレクトリには、Android / Kotlin プロジェクトにおいて **AI Coding Agentの品質を定量的に評価（Evals）** するためのスクリプト、データセット、プロンプトテンプレートが格納されています。

ご自身のAndroidプロジェクト（別リポジトリ）にそのままコピー＆ペーストして流用できる構成になっています。

---

## 📁 ディレクトリ構成

```text
samples/evals/
├── README.md                           # 本ガイド
├── check_agent_diff.py                 # [Grader 1] git diffを解析する決定論的チェッカー
├── run_android_deterministic_eval.sh   # [Runner] Gradle Build + Test + Diffチェックを一括実行
├── dataset/
│   └── eval_dataset.yaml               # [Dataset] 5ケースの実践的タスク定義 (SWE-bench風)
└── judge/
    └── llm_judge_prompt_template.md    # [Judge] LLM-as-a-Judge用の二値判定ルーブリック
```

---

## 🚀 他リポジトリへの導入手順（3ステップ）

### Step 1: ファイルのコピー

評価を行いたい対象のAndroidプロジェクトルートに、本ディレクトリ `samples/evals/` をそのまま配置します。

```bash
# 例: 対象プロジェクトのルートで
mkdir -p evals
cp -r /path/to/kusakabe-dev.github.io/samples/evals/* ./evals/
```

### Step 2: 差分チェッカー（Grader）の単体実行

Agentがコードを変更した直後（またはコミット後）に以下を実行します。

```bash
# ワーキングツリーの変更をチェック
python3 evals/check_agent_diff.py

# または直前コミットをチェック
python3 evals/check_agent_diff.py --diff-target HEAD~1
```

**チェックされる項目:**
- [x] Kotlin強制アンラップ (`!!`) の追加禁止
- [x] 変更ファイル数の上限超過チェック（デフォルト10ファイル）
- [x] 保護対象ファイル（`build.gradle.kts`, `settings.gradle.kts`, `libs.versions.toml` 等）の改変禁止
- [x] `println`, `Log.d`, `TODO` 等の残存警告

### Step 3: フルEvalの実行（Gradle + Diff）

プロジェクトルートでランナーを実行します。

```bash
./evals/run_android_deterministic_eval.sh
```

**実行フロー:**
1. `./gradlew assembleDebug` (ビルド成否)
2. `./gradlew testDebugUnitTest` (テスト通過)
3. `python3 check_agent_diff.py` (差分品質)

すべてクリアした時のみ `exit 0` となり、1つでも失敗すると原因となったステップと所要時間が表示されます。

---

## 📊 自作Eval Datasetの作り方 (`dataset/eval_dataset.yaml`)

過去に解決したGitHub IssueやPRから、以下のようにタスクを切り出します。

1. **タスク要件 (`prompt`)**: Issueの本文から「期待される振る舞い」を抽出
2. **検証用テスト (`verification`)**: そのバグや仕様を検証するための単体テストメソッド名を指定
3. **触って良いファイル (`expected_affected_files`)**: Agentのスコープ逸脱を検知

このデータセットを基に、Agentへタスクを実行させ、`run_android_deterministic_eval.sh` で採点するサイクルを回します。

---

## ⚖️ LLM-as-a-Judge の利用方法 (`judge/`)

単体テストやビルドだけでは判定できない「要件のニュアンス」「過剰実装の有無」を評価したい場合は、`judge/llm_judge_prompt_template.md` を使用します。

1. プロンプトテンプレート内の `{{TASK_PROMPT}}` にタスク要件を挿入
2. `{{GIT_DIFF}}` に `git diff` の出力を挿入
3. 判定役のLLM（Claude, Gemini, GPT等）に入力
4. 出力されるJSON形式のBoolean判定（`requirements_met`, `no_scope_creep` 等）を記録
