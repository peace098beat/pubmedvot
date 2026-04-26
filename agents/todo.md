# 実装 TODO（GitHub Actions に pytest API 疎通テストを追加）

このチェックリストは PR `claude/add-pytest-github-actions-a3VJp` の作業を別エージェントが再現・継続できるように残すものです。チェックを進めながら作業してください。

## 完了済み（このブランチで実施）

- [x] `pytest.ini` を削除し、marker 設定を `pyproject.toml` に統合
- [x] `pyproject.toml` の `[tool.pytest.ini_options].markers` を `api` 1 件に整理
- [x] `tests/conftest.py` を環境ベース判定に書き換え（`GITHUB_ACTIONS=true` または `--run-api` で force-run、それ以外は skip）
- [x] `tests/test_clients.py` の `os.environ[...]` 直接参照を `_require_env()` ヘルパに置換し、CI ではキー欠如時 `pytest.fail`、ローカルでは `pytest.skip` に分岐
- [x] `.github/workflows/test_integration.yml` を `unit` / `api` の 2 ジョブに分離（`api` は `needs: unit`、secrets を注入）
- [x] `agents/` フォルダを新設し、README / todo / design-rationale / knowledge を配置
- [x] `AGENTS.md` をリポジトリ直下に新設
- [x] `CLAUDE.md` のシークレット名 `SLACK_WEBHOOK_URL` → `SLACK_WEBHOOK` 修正、テスト方針節を新方針に書き換え、存在しないファイル参照 (`tests/test_integration.py`) を `tests/test_clients.py` に修正

## マージ後フォローアップ（次のエージェント向け）

- [ ] GitHub リポジトリ Settings > Secrets and variables > Actions に `SLACK_WEBHOOK` と `GEMINI_API_KEY` が登録されていることを確認。未登録なら `api` ジョブが赤くなる（要件 B 通りの挙動だが、運用上は登録しておく）。
- [ ] PR がマージされた後、`main` 上で初回 `api` ジョブが緑になることを確認。
- [ ] CLAUDE.md は `pip install` 系の実 CI と「常に uv を使え」の方針が乖離している。CI を `uv` ベースに統一するか、CLAUDE.md の文言を実態に合わせて緩めるかを別 PR で検討。
- [ ] 純粋ロジックのユニットテスト（XML パース、Block Kit 構造、文字列切り詰め）はまだ無い。CLAUDE.md のテスト方針が言及しているので、別 PR で追加検討。

## 設計を変えたくなったら

`agents/design-rationale.md` を必ず先に読み、変更理由をそこへ追記してから着手してください。
