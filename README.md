# Claude Code Sample Repository

Claude Code を AWS Bedrock 経由で利用するための標準リポジトリです。開発環境は rootless Podman と VS Code Dev Containers で起動します。Docker、Docker Compose、podman-compose は使用しません。

## 前提

- Linux ホストに rootless Podman が導入済みであること
- VS Code に最新安定版の Dev Containers 拡張機能（内部の Dev Containers CLI 0.76.0 以降）が導入済みであること
- 次のいずれかの Bedrock 認証情報を用意できること
  - IAMアクセスキー: ホストの `~/.aws/credentials` に保存した AWS プロファイル
  - Bedrock APIキー: AWS Management Console で生成した long-term API key

Dev Containers の Podman 互換性は Podman 5 以降が公式の目安です。社内標準環境で別バージョンを使う場合は、後述の構成確認が成功することを確認してください。ComposeプロバイダーとPodman APIソケットの設定は、この構成では参照されません。

## 初回設定

### 1. VS Code から Podman を使う

`.vscode/settings.json` で、Dev ContainersとContainer Toolsが使用するコマンドを `podman` に設定済みです。

`dev.containers.dockerPath` という設定名にはDev Containersの互換API名が残っていますが、値は `podman` です。Compose関連の設定は使用しません。

### 2. Bedrock の認証方式を選ぶ

認証方式は `.claude/settings.local.json` の内容だけで切り替えます。ホストでの `export` / `unset` や、認証方式を変えるたびのコンテナ再ビルドは不要です。

このファイルは Dev Container の初回作成時に `.claude/settings.local.json.template` から自動生成され、Git管理対象から除外されます。自動生成時には、他ユーザーから読み取られないようファイル権限を `600` に設定します。

> [!IMPORTANT]
> 認証情報を記入するのは、Git管理外の `.claude/settings.local.json` だけです。`.claude/settings.json` や `.claude/settings.local.json.template` にはAPIキーを書かないでください。

#### A. IAMアクセスキーを使う（従来方式）

`.claude/settings.local.json` を次の内容にします。`bedrock` は `.aws/credentials` で使用しているプロファイル名に合わせて変更できます。

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "env": {
    "AWS_PROFILE": "bedrock"
  }
}
```

ホストの `~/.aws/credentials` に同名のプロファイルを用意します。

```ini
[bedrock]
aws_access_key_id=...
aws_secret_access_key=...
```

`~/.aws` はコンテナの `/home/vscode/.aws` にread-onlyでマウントされます。ホストに `~/.aws` がない場合は、Dev Containers がマウント前に空のディレクトリを自動作成します。

#### B. Bedrock APIキーを使う（long-term）

`.claude/settings.local.json` 全体を次の内容へ置き換え、プレースホルダーを実際のキーに変更します。

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "env": {
    "AWS_BEARER_TOKEN_BEDROCK": "YOUR_BEDROCK_LONG_TERM_API_KEY"
  }
}
```

APIキーに関連付けられた IAM ユーザーには、このリポジトリで指定している推論プロファイルに対する次の権限が必要です。

- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`
- `bedrock:ListInferenceProfiles`
- `bedrock:GetInferenceProfile`

ファイルを保存した後に Claude Code を新しく起動すると、APIキー認証が選択されます。IAM方式へ戻す場合は、同じファイルを A の内容へ戻すだけです。共有設定に `AWS_PROFILE` が残っていても、`AWS_BEARER_TOKEN_BEDROCK` がある場合はAPIキー認証がAWSクレデンシャルチェーンとは別に処理されます。

> [!NOTE]
> AWS は long-term API key を検証・探索用途向けと位置づけ、本番用途には short-term API key を推奨しています。本構成は依頼どおり long-term API key に対応しますが、キーには有効期限と必要最小限の権限を設定してください。

### 3. 必要に応じて環境変数を設定する

`HTTP_PROXY`、`HTTPS_PROXY`、`NO_PROXY` と、それぞれの小文字名は、VS Codeを起動したホスト環境からビルド時とコンテナ実行時の両方へ引き継がれます。必要な値をホスト側でexportしてからVS Codeを起動してください。

```bash
export NO_PROXY=bedrock.ap-northeast-1.amazonaws.com,bedrock-runtime.ap-northeast-1.amazonaws.com
export no_proxy="$NO_PROXY"
code .
```

`/cafe05/${USER}/.env` など既存のenvファイルを利用する場合は、信頼できるファイルであることを確認した上で、同様にホストシェルへ読み込んでから `code .` を実行します。

## 起動

1. このリポジトリをクローンします。
2. VS Code でリポジトリを開きます。
3. `Dev Containers: Reopen in Container` を実行します。
4. コンテナ内のターミナルで `claude` を実行します。

ユーザーごとの手動コンテナ名設定は不要です。Dev Containersがワークスペース単位のコンテナ名とイメージ名を管理します。

認証方式を変更した場合は、実行中の Claude Code を終了して新しく起動します。Dev Container 自体の再作成や、ホスト環境変数の変更は不要です。

### 認証設定を確認する

Claude Code の `/status` で、プロバイダーが Amazon Bedrock であることと、ローカルプロジェクト設定が読み込まれていることを確認できます。APIキーは Bedrock 専用なので、APIキー方式の確認に `aws sts get-caller-identity` は使用できません。最終的な疎通は実際のモデル呼び出しで確認してください。

## 構成の確認

VS Codeと同じDev Containers CLIで起動確認する場合は、次のコマンドを実行します。このコマンドはPodmanを直接呼び出し、Composeは呼び出しません。

```bash
npx --yes @devcontainers/cli up \
  --workspace-folder . \
  --docker-path podman \
  --buildkit never
```

起動後はPodmanがコンテナを管理していることを確認できます。

```bash
podman ps
```

## Podman 運用方針

- `privileged` は使用しません。
- rootless Podmanを使用します。Linux版のDev Containers CLIはPodman利用時に `--security-opt label=disable` と、非rootユーザーに対する `--userns=keep-id` を自動付与します。そのため、同じオプションを `runArgs` へ重複して定義しません。
- `label=disable` により、SELinuxが有効なホストでもワークスペースと `~/.aws` のbind mountを利用できます。一方で、このコンテナに対するSELinuxのラベル分離は無効になるため、信頼できるリポジトリだけを開き、追加の機密ディレクトリを安易にマウントしないでください。AWS認証情報のマウントはread-onlyです。
- Dev ContainersからPodmanのbuild/create/start/execを直接使用し、ComposeとPodman APIソケットは使用しません。
- ビルド定義はOCI互換の `.devcontainer/Containerfile` です。
- 外部のベースイメージは `mcr.microsoft.com/...` の完全修飾名を使用します。
- ワークスペースは `/workspace`、実行ユーザーは `vscode` です。
- `dev.containers.dockerPath` と `devcontainer.json` の `build.dockerfile` はDev Containers仕様上の互換名です。実際のコマンドはPodman、実際のファイル名は `Containerfile` です。

## Claude Code / Bedrock の設定

Claude Code の Bedrock 利用設定は `.claude/settings.json` に定義しています。利用モデルやリージョンを変更する場合は、同ファイルの `ANTHROPIC_MODEL`、`ANTHROPIC_SMALL_FAST_MODEL`、`AWS_REGION` を更新します。

認証に関する役割分担は次のとおりです。

- `.claude/settings.json`: Bedrock有効化、リージョン、モデル、共有のIAMプロファイル初期値
- `.claude/settings.local.json.template`: IAM方式の安全な初期テンプレート（Git管理対象）
- `.claude/settings.local.json`: ユーザーがIAM/APIキー方式を選ぶローカル設定（Git管理外）
- `.devcontainer/devcontainer.json`: `~/.aws` とローカル設定ファイルの初期準備を自動化

APIキーはローカル設定ファイルから Claude Code のセッションだけに設定されます。ホスト環境からの `AWS_BEARER_TOKEN_BEDROCK` 転送は行いません。

社内LANからDirect Connect経由でBedrockに接続する場合は、前述の手順で `NO_PROXY` と `no_proxy` をホスト環境へ設定します。コンテナ内では `echo "$no_proxy"` と `curl -v https://bedrock-runtime.ap-northeast-1.amazonaws.com` で経路を確認できます。

## 参考リンク

- [VS Code: Alternate ways to install Docker (Podman)](https://code.visualstudio.com/remote/advancedcontainers/docker-options)
- [Dev Containers CLI: Change Log](https://github.com/devcontainers/cli/blob/main/CHANGELOG.md)
- [Podman: Volume mount permission denied (SELinux)](https://github.com/containers/podman/blob/main/troubleshooting.md#2-cant-use-volume-mount-get-permission-denied)
- [Dev Container: Using Images and Container Build Files](https://containers.dev/guide/dockerfile)
- [VS Code: Environment variables](https://code.visualstudio.com/remote/advancedcontainers/environment-variables)
- [Claude Code 公式ドキュメント](https://code.claude.com/docs/ja/overview)
- [Claude Code settings](https://code.claude.com/docs/en/configuration)
- [Claude Code on Amazon Bedrock](https://code.claude.com/docs/en/amazon-bedrock)
- [Amazon Bedrock: API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html)
- [Amazon Bedrock: Use an API key](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-use.html)
- [AWS Bedrock 対応モデル一覧](https://docs.aws.amazon.com/ja_jp/bedrock/latest/userguide/inference-profiles-support.html)
