# CLAUDE.md

このファイルは、リポジトリ内のコードを操作する際に Claude Code (claude.ai/code) へのガイダンスを提供します。

## プロジェクトの目的

**pubmedvot** は PubMed → Gemini → Slack パイプラインです。NCBI E-utilities から最新の研究論文を取得し、Gemini でタイトルとアブストラクトを日本語に翻訳して、Block Kit を使用して Slack にフォーマット済みサマリーを投稿します。GitHub Actions のスケジュール（毎週月曜・火曜 09:00 JST）で自動実行されます。

## ツールチェーン

依存関係の管理には **uv**、リント・フォーマットには **ruff**、テストには **pytest** を使用します。`pip install` や `venv` は使わず、常に `uv` を使用してください。

```bash
uv sync --extra dev          # dev を含む全依存関係をインストール
uv run pytest tests/ -v      # ユニットテストを全て実行
uv run pytest tests/test_integration.py -v -m integration  # 実API テスト
uv run ruff check src/ tests/  # リント
uv run ruff format src/ tests/ # フォーマット
```

単一のテストファイルまたはテストを実行する場合:
```bash
uv run pytest tests/test_pubmed.py -v
uv run pytest tests/test_pubmed.py::TestSearchPubMed::test_returns_articles -v
```

ローカルでパイプラインを実行する場合（シークレットが必要）:
```bash
SCHEDULE_DAY=monday SLACK_WEBHOOK_URL=... GEMINI_API_KEY=... uv run python -m src.main
DEBUG_MODE=true SCHEDULE_DAY=monday SLACK_WEBHOOK_URL=... uv run python -m src.main
```

## Git ワークフロー

**`main` への直接プッシュは禁止です。** すべての変更はプルリクエストを通して行います:
1. フィーチャーブランチを作成: `git checkout -b feat/your-feature`
2. 変更をコミットし、`git push -u origin feat/your-feature`
3. PR を作成 — マージ前に CI が通過していること

## アーキテクチャ

パイプラインは `src/main.py` による線形4段階のオーケストレーションです:

```
config/settings.yaml  +  環境変数 (SCHEDULE_DAY, SLACK_WEBHOOK_URL, GEMINI_API_KEY)
         ↓
src/pubmed_client.py   – NCBI E-utilities (esearch JSON → efetch XML → Article dataclass)
         ↓
src/translator.py      – Gemini API (list_models → generateContent 対応モデルを選択 → 翻訳)
         ↓
src/slack_client.py    – Slack Block Kit (build_blocks → webhook URL へ POST)
```

**`config/settings.yaml`** は曜日ごとのスケジュール（`topic`、`query`、`top_n`、`days_back`、`translate`）と、`debug` オーバーライド（1件・翻訳なし）を定義します。

**`Article` データクラス** (`src/pubmed_client.py`) は各レイヤー間の唯一のデータコントラクトです: `pmid`、`title`、`authors`、`abstract`、`pub_date`、`url`。翻訳処理は `title` と `abstract` をインプレースで書き換えます。

**Gemini モデル選択** (`src/translator.py`) は実行時に `list_models()` を呼び出し、`generateContent` をサポートする最初のモデルを選択します。優先順位: `gemini-2.0-flash`、`gemini-2.0-flash-lite`、`gemini-1.5-flash`、`gemini-1.5-flash-latest`、`gemini-pro`。API キーがない場合やエラーが発生した場合は、`was_translated=False` で元のテキストに静かにフォールバックします。

**NCBI レート制限**: リクエスト間に 0.4 秒の遅延を設けています。NCBI ポリシーに従い、全リクエストに `User-Agent`、`tool`、`email` パラメータを含めてください（違反すると 403 IP ブロックが発生します）。

**Slack Block Kit 制限**: テキストフィールドはブロックあたり最大 2900 文字に切り詰められます。

## テスト方針

モックよりも実際の API 呼び出しを優先してください。`tests/test_integration.py` の統合テストは NCBI・Gemini・Slack の実エンドポイントに接続し、正確性の最終判断基準となります。他のテストファイルのユニットテストは、純粋なロジック（XML パース、Block Kit ペイロード構造、文字列切り詰め）に対しては許容されますが、実エンドポイントが利用可能な場合は外部 HTTP 呼び出しをモックすべきではありません。

統合テストはシークレットが存在しない場合に `pytest.skip` で穏やかにスキップします — 環境変数の欠如でテストが失敗してはいけません。

## CI/CD

- **`test_integration.yml`**: 全プッシュ・PR で実行 — ユニットテストは常に実行、シークレットがある場合は統合テストとデバッグ Slack 投稿も実行。
- **`pubmed_notify.yml`**: cron スケジュール（月・火 00:00 UTC）+ `schedule_day` 入力付きの `workflow_dispatch`。

必要なシークレット: `SLACK_WEBHOOK_URL`（必須）、`GEMINI_API_KEY`（任意・未設定の場合は翻訳が無効化されます）。
