# Claude Code Sample Repository

Claude Code を AWS Bedrock 経由で利用するための標準リポジトリです。開発環境は rootless Podman と VS Code Dev Containers で起動します。Docker デーモンは使用しません。

## 前提

- Linux ホストに rootless Podman が導入済みであること
- `podman compose version` が成功すること
- rootless Podman ソケットが起動していること
- VS Code に Dev Containers 拡張機能が導入済みであること
- ホストの `~/.aws/credentials` に Bedrock 用の AWS 認証情報があること

Dev Containers の Podman 互換性は Podman 5 以降が公式の目安です。社内標準環境で別バージョンを使う場合は、本リポジトリの構成検証コマンドが成功することを確認してください。

Podman Compose が利用するユーザーソケットを起動します。

```bash
systemctl --user start podman.socket
systemctl --user is-active podman.socket
```

ログイン後に自動起動させる運用が許可されている場合は、`systemctl --user enable --now podman.socket` で有効化できます。

## 初回設定

### 1. VS Code から Podman を使う

VS Code のユーザー設定 `settings.json` に以下を追加します。

```json
{
  "dev.containers.dockerPath": "podman",
  "dev.containers.dockerComposePath": "podman",
  "dev.containers.dockerSocketPath": "${XDG_RUNTIME_DIR}/podman/podman.sock"
}
```

設定名には互換 API の都合で `docker` が残っていますが、実行コマンドには `podman` を指定しています。Container Tools 拡張機能向けの Podman 設定は `.vscode/settings.json` に定義済みです。

### 2. AWS 認証情報を用意する

`.claude/settings.json` の `AWS_PROFILE` はデフォルトで `bedrock` です。ホストの `~/.aws/credentials` に同名のプロファイルを用意します。

```ini
[bedrock]
aws_access_key_id=...
aws_secret_access_key=...
```

`~/.aws` はコンテナの `/home/vscode/.aws` に read-only でマウントされます。別のプロファイル名を使う場合は `.claude/settings.json` の `AWS_PROFILE` を変更してください。

### 3. 必要に応じて環境変数を設定する

Compose は以下の任意ファイルを読み込みます。どちらも存在しない場合は無視されます。

- `.devcontainer/.env`: このリポジトリのコンテナだけで使う値
- `/cafe05/${USER}/.env`: スパコン環境でユーザーが共通利用する値

`.devcontainer/.sample.env` をコピーして利用できます。`.env` は Git 管理対象外です。ホストの大文字・小文字の proxy 環境変数もビルド時と実行時に引き継ぎます。

## 起動

1. このリポジトリをクローンします。
2. VS Code でリポジトリを開きます。
3. `Dev Containers: Reopen in Container` を実行します。
4. コンテナ内のターミナルで `claude` を実行します。

ユーザーごとの手動コンテナ名設定は不要です。Compose のプロジェクト名と `localhost/claude-code-sample:dev-${USER}` イメージ名で分離します。

## 構成の確認

Dev Container を起動する前に、次のコマンドで Compose 設定を検証できます。

```bash
podman compose \
  -f .devcontainer/compose.yaml \
  -f .devcontainer/compose.dev.yaml \
  config
```

起動後は次のコマンドで、Docker ではなく Podman がコンテナを管理していることを確認できます。

```bash
podman ps
podman images localhost/claude-code-sample
```

## Podman 運用方針

- `privileged` は使用しません。
- rootless Podman と `userns_mode: keep-id` を使用します。
- 外部のベースイメージは `mcr.microsoft.com/...`、生成イメージは `localhost/...` の完全修飾名を使用します。
- ワークスペースは `/workspace`、実行ユーザーは `vscode` です。
- `Dockerfile` と `devcontainer.json` の `dockerComposeFile` は Dev Containers / OCI ツール間で使われる互換上の名称です。コンテナのビルドと実行は Podman が担当します。

## Claude Code / Bedrock の設定

Claude Code の Bedrock 利用設定は `.claude/settings.json` に定義しています。利用モデルやリージョンを変更する場合は、同ファイルの `ANTHROPIC_MODEL`、`ANTHROPIC_SMALL_FAST_MODEL`、`AWS_REGION` を更新します。

社内 LAN から Direct Connect 経由で Bedrock に接続する場合は、必要に応じて `.devcontainer/.env` または `/cafe05/${USER}/.env` に次のような設定を追加します。

```dotenv
no_proxy=bedrock.ap-northeast-1.amazonaws.com,bedrock-runtime.ap-northeast-1.amazonaws.com
NO_PROXY=bedrock.ap-northeast-1.amazonaws.com,bedrock-runtime.ap-northeast-1.amazonaws.com
```

コンテナ内では `echo "$no_proxy"` と `curl -v https://bedrock-runtime.ap-northeast-1.amazonaws.com` で経路を確認できます。

## 参考リンク

- [VS Code: Alternate ways to install Docker (Podman)](https://code.visualstudio.com/remote/advancedcontainers/docker-options)
- [Claude Code 公式ドキュメント](https://code.claude.com/docs/ja/overview)
- [AWS Bedrock 対応モデル一覧](https://docs.aws.amazon.com/ja_jp/bedrock/latest/userguide/inference-profiles-support.html)
