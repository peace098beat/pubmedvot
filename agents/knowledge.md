# ナレッジ：本プロジェクトで使っている仕組みのリファレンス

設計根拠は `design-rationale.md`、TODO は `todo.md` を参照。ここでは「pytest と GitHub Actions の挙動」のうち、本プロジェクトの判断に直結する部分だけを短くまとめる。

## pytest marker

- `@pytest.mark.api` を付けると、そのテストが特定カテゴリに分類される。
- `pyproject.toml` の `[tool.pytest.ini_options].markers` に登録しないと `PytestUnknownMarkWarning` が出るため必ず登録する。
- CLI でフィルタ可能:
  - `pytest -m "api"` — api だけ実行
  - `pytest -m "not api"` — api 以外を実行
  - `pytest -m "api and not slow"` — 論理結合も可

## `pytest_collection_modifyitems`

- conftest.py に定義すると、**テスト収集後・実行前** にすべての `item`（テスト関数）を改変できる。
- 本プロジェクトでは `force_run` が偽のときに `api` marker のテストへ追加で `pytest.mark.skip` を貼る。これにより「marker 自体は維持しつつ実行は止める」が実現できる。

## `pytest.fail` vs `pytest.skip`

| 関数 | 結果 | 用途 |
|---|---|---|
| `pytest.fail(msg)` | テストが **失敗（red）** | 「ここまで到達したら不正な状態」と表明したいとき |
| `pytest.skip(msg)` | テストが **スキップ（yellow）** | 「条件が揃わないので評価できない」とき |
| `pytest.xfail(msg)` | 失敗を期待。失敗なら xfail、成功なら xpass | 既知の欠陥を仮置きするとき |

本プロジェクトは「CI ではキー欠如 = 不正状態」と扱うので `pytest.fail` を採用。

## GitHub Actions が自動付与する環境変数

- `GITHUB_ACTIONS=true` — GitHub Actions ランナー上で必ず立つ。
- `CI=true` — GitHub Actions 含むほぼ全 CI で立つが、他 CI と区別したいときは `GITHUB_ACTIONS` を見るほうが正確。
- 公式リファレンス: https://docs.github.com/en/actions/learn-github-actions/variables#default-environment-variables

本プロジェクトは「GitHub Actions 上か否か」を判定したいので `GITHUB_ACTIONS` を採用。

## ワークフローでの secrets 注入

- `secrets.<NAME>` は **環境変数として注入する** のが Python から読める唯一のパス。
- `env:` ブロックでマッピングしないとプロセスからは見えない（ステップの引数文字列に直接埋めるのは秘密がログに残るリスクあり、推奨しない）。
- secrets 未登録時は空文字列が注入されるため、Python 側は `os.environ.get(name) or fallback` で必ず判定すること。

## pytest 終了コード

- `0` 全 pass / `1` 失敗あり / `2` 中断 / `3` 内部エラー / `4` 使い方エラー / **`5` テストが 1 件も収集されなかった**
- `-m "not api"` のように marker フィルタで 0 件になると `5` で abort され、CI は failure 扱いになる。本プロジェクトの workflow はそれを許容するため `|| test $? -eq 5` を付けている（純粋ロジックのユニットテストが追加されたら外してよい）。

## 本プロジェクトのテスト実行コマンド早見表

| 目的 | コマンド |
|---|---|
| ユニット系のみ（API 叩かない） | `python3 -m pytest tests/ -v -m "not api"` |
| API 疎通のみ（ローカルで opt-in） | `python3 -m pytest tests/ -v --run-api -m "api"` |
| 全実行（CI と同等の挙動を再現） | `GITHUB_ACTIONS=true SLACK_WEBHOOK=... GEMINI_API_KEY=... python3 -m pytest tests/ -v` |
| デフォルト（api は skip される） | `python3 -m pytest tests/ -v` |

## 関連ファイルの場所

- `tests/conftest.py` — marker 制御ロジックの本体
- `tests/test_clients.py` — `_require_env` ヘルパと 3 つの API 疎通テスト
- `pyproject.toml` — marker 登録
- `.github/workflows/test_integration.yml` — unit / api 2 ジョブ
