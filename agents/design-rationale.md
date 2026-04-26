# 設計根拠：pytest API 疎通テストの marker 戦略と CI 連携

## 背景と問題

pubmedvot は PubMed → Gemini → Slack の 3 つの実 API に依存する線形パイプライン。各 API の疎通が壊れていないかを CI で常時検証したい一方、

- **ローカル開発者は API キーを持たないことがある** → ローカルでは API テストを強制したくない（任意 opt-in）
- **GitHub Actions では secrets が必ず揃っている前提** → CI ではキー欠如は **失敗** として検出したい（skip ではない）

という非対称な要件がある。

## 採用した方針

### 1. marker 名は `api` に統一

- 採用前の状態: `pytest.ini` は `api`、`pyproject.toml` は `integration` と二重定義・名前不一致だった。
- `integration` は意味が広い（DB 統合・サービス間統合など）ため避け、「実 API を叩く疎通テスト」をそのまま表す `api` を採用。
- 設定ファイルは `pyproject.toml` 1 本に統合（`pytest.ini` は削除）。Python ツールチェーンの慣例に沿う。

### 2. force-run のトリガは「環境」ベース

`tests/conftest.py` の `pytest_collection_modifyitems` で次のように判定:

```python
force_run = os.environ.get("GITHUB_ACTIONS", "").lower() == "true" or config.getoption("--run-api")
```

- `GITHUB_ACTIONS=true` は GitHub Actions が自動付与する環境変数（ローカルや他 CI には立たない）。これにより **ワークフロー側で `--run-api` を渡し忘れても CI では強制実行** になる。
- ローカルでは `pytest --run-api` で明示的に opt-in できる。
- 何も指定しなければ `api` marker のテストは skip。

### 3. キー欠如時の振る舞いは CI とローカルで分岐

`tests/test_clients.py` の `_require_env()` ヘルパが各 API テストの先頭で呼び出され、

- `GITHUB_ACTIONS=true` かつキー無し → `pytest.fail()` で **明示的に失敗**
- ローカル（`--run-api` 指定中でも）かつキー無し → `pytest.skip()` で **穏やかにスキップ**

この振る舞いが **要件 B（CI ではキー必須）** を実装上で担保する。`pytest.fail` と `pytest.skip` の差は `agents/knowledge.md` 参照。

### 4. CLAUDE.md 旧方針の意図的な上書き

採用前の CLAUDE.md には「統合テストはシークレットが存在しない場合に `pytest.skip` で穏やかにスキップします — 環境変数の欠如でテストが失敗してはいけません」とあったが、これはローカル開発者の利便性のみを考慮した方針。今回 CI で「キー欠如＝即失敗」を要件として受け入れたため、CLAUDE.md 本体を新方針に書き換え、ここにも理由を残す。**ローカルでの skip 挙動は維持されている** ので、ローカル開発者の体験は変わらない。

### 5. ワークフローを `unit` / `api` の 2 ジョブに分離

- `unit` ジョブ: `-m "not api"` で常時実行。secrets 不要。PR の早期フィードバックを担う。
- `api` ジョブ: `needs: unit` で unit 通過後のみ。`SLACK_WEBHOOK` と `GEMINI_API_KEY` を注入。`-m "api"` で API テストのみ実行。
- 分離の理由:
  - secrets が必要なジョブを最小化することでセキュリティ表面積を下げる（unit ジョブは fork PR でも安全に動かせる素地ができる、将来的に）。
  - unit が壊れている時に API ジョブを走らせても無駄な API コール・無駄な Slack 投稿が増える。`needs: unit` で防ぐ。
  - 失敗時のログ分離が容易。

### 6. `--run-api` フラグは CI では渡さない

- CI 側は `GITHUB_ACTIONS=true` で十分なので、ワークフローからフラグを削除した。
- フラグは「ローカルでの opt-in」専用に役割を絞った。

## 採用しなかった代替案

- **キー有無だけで自動判定**（`SLACK_WEBHOOK` があれば実行、無ければ skip） → CI で secrets 設定漏れを検出できないので不採用。
- **`pytest-env` でキー欠如時に xfail** → xfail は「失敗が期待される」意味で、運用上の意図がブレる。`pytest.fail` の方が意図が明示的。
- **GitHub Actions 側でキー存在チェックして `if:` でジョブをスキップ** → 「無いから動かない」を許してしまい、要件 B（CI ではキー必須）が壊れる。
- **`api` marker を廃して CI 専用に test ファイルを分割** → ローカルからの opt-in 実行 (`--run-api`) ができなくなり、開発体験が落ちる。

## 影響範囲

- 本番通知 (`pubmed_notify.yml`) は今回触っていない。テスト戦略変更は通知パイプラインに影響しない。
- `pyproject.toml` の `[tool.pytest.ini_options]` を変えたので、`pytest --markers` の出力が変化（旧 `integration` → 新 `api`）。

## 変えたくなったら

この設計を変えるときは、ここに「変更理由」「採用しなかった代替」「影響範囲」を追記してから着手してください。
