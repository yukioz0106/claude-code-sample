# Snowflake接続（OAuth / Entra ID）

Snowflakeにある DB データを参照するための接続モジュール。認証はユーザー名・パスワードではなく、Entra ID (Azure AD) のデバイスコードOAuthでトークンを取得し、Snowflakeへ `authenticator="oauth"` で接続する。

参考: [eneos-hdai/ss-digital-support の ml/notebooks/20_datasets/manual_updates](https://github.com/eneos-hdai/ss-digital-support/tree/fix/ml-environment-settings/ml/notebooks/20_datasets/manual_updates)（同構成のOAuth接続パターンを移植）

## セットアップ

1. 依存パッケージをインストールする。

   ```bash
   pip install -r snowflake_connect/requirements.txt
   ```

2. [.env.example](.env.example) を参考に、リポジトリ直下の `.env`（Git管理外）に以下を設定する。

   | 環境変数 | 内容 |
   | --- | --- |
   | `SNOWFLAKE_ACCOUNT` | Snowflakeアカウント識別子 |
   | `SNOWFLAKE_OAUTH_USER` | OAuth認証で接続する操作者のユーザー |
   | `MSAL_SF_TENANT_ID` | Entra IDのテナントID（GUID） |
   | `MSAL_SF_CLIENT_ID` | デバイスコード認証に使うEntra IDアプリのクライアントID（GUID） |
   | `MSAL_SF_APPLICATION_ID_URI` | Snowflake向けApplication ID URI（末尾の`/.default`は付けない） |

   これらはSnowflake/Entra ID管理者に発行してもらう値。

3. ロール・ウェアハウス・データベース・スキーマは [snowflake_oauth.yml](snowflake_oauth.yml) に設定する（Git管理対象、機密情報は含まない）。

## 接続確認

```bash
python snowflake_connect/snowflake_oauth.py
```

表示されたURLとコードでブラウザーからサインインする。成功すると `CURRENT_USER()` などの接続情報が表示される。取得したトークンは `snowflake_oauth.yml` の `OAUTH_TOKEN_CACHE`（既定: `~/.snowflake/snowflake_oauth_token_cache.json`、リポジトリ外・本人のみ読み書き可）に保存され、有効期限内は再利用される。キャッシュが壊れた場合は該当ファイルを削除して再実行する。

## データの参照

```python
from snowflake_connect.query import run_query

df = run_query("SELECT * FROM your_table LIMIT 100")
```

`run_query` は読み取り専用の用途を想定している。接続はリクエストごとに開き、終了後に閉じる。
