# AGENTS.md

pubmedvot は PubMed → Gemini → Slack の自動通知パイプラインです。エージェント（Claude Code 等）がこのリポジトリで作業するときの入口ファイルです。

## まず読むべきもの

1. **`CLAUDE.md`** — プロジェクト全体のアーキテクチャ・ツールチェーン・コーディング規約
2. **`agents/README.md`** — エージェント向けナレッジベースの読み順
3. **`agents/todo.md`** — 進行中タスク・マージ後フォローアップ
4. **`agents/design-rationale.md`** — 設計判断の根拠（テスト戦略・CI 構成）
5. **`agents/knowledge.md`** — pytest / GitHub Actions の挙動リファレンス

## テスト戦略の要約

- pytest marker `api` を付けたテスト（`tests/test_clients.py` の 3 件）が「実 API 疎通テスト」。
- **ローカルではデフォルト skip。** 任意実行は `python3 -m pytest tests/ --run-api -v`。
- **GitHub Actions では `GITHUB_ACTIONS=true` を検出して強制実行。** `SLACK_WEBHOOK` / `GEMINI_API_KEY` 欠如時は skip ではなく **fail** する（要件として CI でキー必須）。
- 詳細は `agents/design-rationale.md` を参照。

## 設計を変えるとき

`agents/design-rationale.md` を必ず読み、変更理由・採用しなかった代替・影響範囲をそこに追記してから着手してください。
