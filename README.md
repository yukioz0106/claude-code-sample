# Claude Code Sample Repository

Claude Code を AWS Bedrock 経由で利用するための標準リポジトリです。開発環境は rootless Podman と VS Code Dev Containers で起動します。Docker、Docker Compose、podman-compose は使用しません。

## 前提

- Linux ホストに rootless Podman が導入済みであること
- VS Code に最新安定版の Dev Containers 拡張機能（内部の Dev Containers CLI 0.76.0 以降）が導入済みであること
- 次のいずれかの Bedrock 認証情報を用意できること
  - IAMアクセスキー: ホストの `~/.aws/credentials` に保存した AWS プロファイル
  - Bedrock APIキー: AWS Management Console で生成した long-term API key

Dev Containers の Podman 互換性は Podman 5 以降が公式の目安です。社内標準環境で別バージョンを使う場合は、後述の構成確認が成功することを確認してください。ComposeプロバイダーとPodman APIソケットの設定は、この構成では参照されません。

## 利用手順

### 1. ローカル設定を作成し、AWSプロファイル名を設定する

1. このリポジトリをクローンします。
2. `.claude/settings.local.json.template` を同じディレクトリへコピーし、コピーしたファイルの名前を `.claude/settings.local.json` に変更します。
3. 作成した `.claude/settings.local.json` の `AWS_PROFILE` を、ホストの `~/.aws/credentials` で使用するプロファイル名に変更します。テンプレートの `bedrock` と同名のプロファイルを使用する場合、値の変更は不要です。
4. VS Codeでリポジトリを開きます。

`.claude/settings.local.json` はGit管理対象外のユーザー設定です。クローン直後には存在しないため、各ユーザーがテンプレートから作成してください。

### 2. 認証情報を用意する

ホストの `~/.aws/credentials` に、手順1で確認したプロファイル名のセクションを用意します。

```ini
[your-profile]
# IAMアクセスキー方式で使用します。
aws_access_key_id=...
aws_secret_access_key=...

# Bedrock APIキー方式にするときだけ、次の行をコメント解除します。
# AWS_BEARER_TOKEN_BEDROCK=YOUR_BEDROCK_LONG_TERM_API_KEY
```

IAMアクセスキー方式では、アクセスキーの2項目を設定し、`AWS_BEARER_TOKEN_BEDROCK` はコメントアウトするか削除します。
Bedrock APIキー方式では、同じプロファイル内の`AWS_BEARER_TOKEN_BEDROCK` を有効にして実際のAPIキーを記載します。APIキー方式だけを使う場合、アクセスキーの2項目は省略できます。

### 3. Dev Containerを起動する

1. `Dev Containers: Reopen in Container` を実行します。
2. コンテナ内のターミナルで `claude` を実行します。

`/status` で、プロバイダーが Amazon Bedrock になっていることを確認します。最終的な認証・接続確認は、実際のモデル呼び出しで行ってください。

## 補足

### Podman / Dev Containers

`.vscode/settings.json` で、Dev ContainersとContainer Toolsが使用するコマンドを `podman` に設定済みです。利用者による設定変更は不要です。

`dev.containers.dockerPath` という設定名にはDev Containersの互換API名が残っていますが、値は `podman` です。Compose関連の設定は使用しません。コンテナ名とイメージ名もDev Containersがワークスペース単位で管理します。

### 認証方式の切替と内部動作

`AWS_BEARER_TOKEN_BEDROCK` 行が有効な場合、アクセスキーが同じプロファイルに残っていても、Claude CodeのBedrock呼び出しにはAPIキー認証が使用されます。この行をコメントアウトまたは削除すればIAM方式へ戻ります。認証方式を変えるための `export` / `unset`、プロファイルの分割、Dev Containerの再作成は不要です。変更後は実行中のClaude Codeを終了して、再度起動してください。

> [!IMPORTANT]
> `AWS_BEARER_TOKEN_BEDROCK` はAWS標準のshared credentials項目ではなく、このリポジトリのランチャーが解釈する独自の互換項目です。AWS公式仕様で `credentials` に保存できる標準項目は `aws_access_key_id`、`aws_secret_access_key`、`aws_session_token` の3つだけです。他のAWS SDKやツールがこのAPIキー項目を読み込むことは期待しないでください。

ランチャーは `.claude/settings.local.json`、`.claude/settings.json`、`~/.claude/settings.json` の順に `AWS_PROFILE` を探索し、選択されたプロファイルだけを読みます。シェルですでに `AWS_PROFILE` が設定されている場合は、その値を最優先します。

以前の構成で `.claude/settings.local.json` に `AWS_BEARER_TOKEN_BEDROCK` を保存していた場合は、その項目を削除して `~/.aws/credentials` へ移してください。`AWS_PROFILE` だけをローカル設定ファイルに残すことは可能です。

`~/.aws` はコンテナの `/home/vscode/.aws` にread-onlyでマウントされます。ホストに `~/.aws` がない場合は、Dev Containersがマウント前に空のディレクトリを自動作成します。`credentials` は平文の秘密情報なので、所有者以外が読み取れない権限で管理してください。APIキーはBedrock専用であるため、APIキー方式の確認に `aws sts get-caller-identity` は使用できません。

### Bedrockの権限とAPIキー

Bedrock APIキーに関連付けられたIAMユーザーには、このリポジトリで指定している推論プロファイルに対する次の権限が必要です。

- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`
- `bedrock:ListInferenceProfiles`
- `bedrock:GetInferenceProfile`

> [!NOTE]
> AWSはlong-term API keyを検証・探索用途向けと位置づけ、本番用途にはshort-term API keyを推奨しています。本構成はlong-term API keyに対応しますが、キーには有効期限と必要最小限の権限を設定してください。

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

- `.claude/settings.local.json.template`: クローン直後に存在するローカル設定のひな形（Git管理対象）
- `.claude/settings.local.json`: テンプレートから各ユーザーが作成し、使用するAWSプロファイルを指定する設定（Git管理対象外）
- `.claude/settings.json`: Bedrock有効化、リージョン、モデル、共有のAWSプロファイル初期値
- `~/.aws/credentials`: 同じAWSプロファイル内にIAMアクセスキーと、必要に応じてBedrock APIキーを保存
- `.devcontainer/claude_bedrock_profile.py`: 選択中プロファイルのAPIキーをClaude Code起動時だけ正式な環境変数へ変換
- `.devcontainer/devcontainer.json`: `~/.aws` のread-onlyマウントと、マウント元ディレクトリの初期準備

ランチャーはAPIキーの値を出力せず、コンテナイメージやリポジトリにも保存しません。APIキー行がない場合は環境変数を追加せず、Claude Codeは従来のAWSクレデンシャルチェーンを使用します。


## 参考リンク

- [VS Code: Alternate ways to install Docker (Podman)](https://code.visualstudio.com/remote/advancedcontainers/docker-options)
- [Dev Containers CLI: Change Log](https://github.com/devcontainers/cli/blob/main/CHANGELOG.md)
- [Podman: Volume mount permission denied (SELinux)](https://github.com/containers/podman/blob/main/troubleshooting.md#2-cant-use-volume-mount-get-permission-denied)
- [Dev Container: Using Images and Container Build Files](https://containers.dev/guide/dockerfile)
- [Claude Code 公式ドキュメント](https://code.claude.com/docs/ja/overview)
- [Claude Code settings](https://code.claude.com/docs/en/configuration)
- [Claude Code on Amazon Bedrock](https://code.claude.com/docs/en/amazon-bedrock)
- [Amazon Bedrock: API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html)
- [Amazon Bedrock: Use an API key](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-use.html)
- [AWS SDKs: Shared config and credentials files](https://docs.aws.amazon.com/sdkref/latest/guide/file-format.html)
- [AWS Bedrock 対応モデル一覧](https://docs.aws.amazon.com/ja_jp/bedrock/latest/userguide/inference-profiles-support.html)
