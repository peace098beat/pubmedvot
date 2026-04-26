# agents/

このフォルダは pubmedvot の自動化エージェント（Claude Code など）が、過去の設計判断と実装手順を再現するために参照するナレッジベースです。

## 読む順番

1. **`todo.md`** — 今やるべきタスクのチェックリスト。実装エージェントはここから消化する。
2. **`design-rationale.md`** — なぜ今のテスト戦略（pytest marker `api` / GITHUB_ACTIONS 環境検出 / CI で fail 強制）になっているのかの根拠。設計を変える前に必ず読む。
3. **`knowledge.md`** — pytest marker、`pytest_collection_modifyitems`、GitHub Actions の自動環境変数、`pytest.fail` vs `pytest.skip` の挙動など、本プロジェクトで使っている仕組みのリファレンス。

## 入口

このフォルダの存在はリポジトリ直下の `AGENTS.md` および `CLAUDE.md` の「テスト方針」節からリンクされています。新しい設計判断を加えるときは、対応する rationale をこのフォルダに残してください。
