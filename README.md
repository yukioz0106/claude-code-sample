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

### 1. Dev Containerを起動する

1. このリポジトリをクローンします。
2. VS Codeでリポジトリを開きます。
3. `Dev Containers: Reopen in Container` を実行します。

クローン直後は既存コンテナがないため、`Reopen in Container`でイメージのビルドとコンテナの作成まで実行されます。

以前のリポジトリ構成ですでにDev Containerを作成済みの場合や、`.devcontainer/Containerfile`または`.devcontainer/devcontainer.json`の更新を取得した場合は、古いイメージやコンテナ設定を使わないよう、`Dev Containers: Rebuild and Reopen in Container`を実行してください。

### 2. Bedrockの認証方式を選ぶ

#### A. IAMアクセスキーを使う

IAMアクセスキー方式では、`.claude/settings.local.json`を作成しません。Git管理対象の`.claude/settings.json`にある`AWS_PROFILE`を、ホストの`~/.aws/credentials`で使用するプロファイル名に変更します。両方で同じ`bedrock`を使用する場合、変更は不要です。

```json
{
  "env": {
    "AWS_PROFILE": "bedrock"
  }
}
```

ホストの`~/.aws/credentials`に同名のプロファイルを用意します。

```ini
[bedrock]
aws_access_key_id=...
aws_secret_access_key=...
```

以前にAPIキー方式を使用し、`.claude/settings.local.json`が残っている場合は削除してください。ローカル設定は共有設定より優先されるため、APIキーが残っているとIAMアクセスキー方式へ切り替わりません。

#### B. Bedrock APIキーを使う（long-term）

クローン直後には`.claude/settings.local.json`は存在しません。次のコマンドでAPIキー専用テンプレートを`.claude/settings.local.json`へリネームし、所有者だけが読み書きできる権限に変更します。

```bash
mv .claude/settings.local.json.template .claude/settings.local.json
chmod 600 .claude/settings.local.json
```

Git管理外の`.claude/settings.local.json`を開き、プレースホルダーを実際のAPIキーに変更します。

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "env": {
    "AWS_BEARER_TOKEN_BEDROCK": "YOUR_BEDROCK_LONG_TERM_API_KEY"
  }
}
```

> [!IMPORTANT]
> APIキーを記入するのは、Git管理外の`.claude/settings.local.json`だけです。Git管理対象の`.claude/settings.json`には記入しないでください。

APIキーに関連付けられたIAMユーザーには、APIキーの使用を許可する`bedrock:CallWithBearerToken`が必要です。long-term API keyだけに限定する場合は、次のポリシー文をIAMユーザーへ追加します。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowBedrockLongTermApiKey",
      "Effect": "Allow",
      "Action": "bedrock:CallWithBearerToken",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "bedrock:bearerTokenType": "LONG_TERM"
        }
      }
    }
  ]
}
```

これとは別に、このリポジトリで指定している推論プロファイルへの次の権限も必要です。

- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`
- `bedrock:ListInferenceProfiles`
- `bedrock:GetInferenceProfile`

`bedrock:CallWithBearerToken`の403が表示された場合は、コンテナやAPIキーの読込みではなく、APIキーに関連付けられたIAMユーザーの権限不足です。エラーに`Please run /login`と表示されても、Bedrock認証は`/login`では解決しません。上記ポリシーを確認してください。OrganizationsのSCP、permissions boundary、または明示的なDenyがある場合は、Allowを追加しても拒否されるため、管理者による確認が必要です。

### 3. Claude Codeを起動する

コンテナ内のターミナルで次のコマンドを実行します。

```bash
claude
```

Claude Codeの`/status`で、プロバイダーがAmazon Bedrockであることと、意図した設定ソースが読み込まれていることを確認します。最終的な疎通は、実際にプロンプトを送信して確認してください。

`.claude/settings.json`または`.claude/settings.local.json`だけを変更した場合は、実行中のClaude Codeを終了して新しく起動すれば反映されます。Dev Containerの再作成は不要です。

## 補足

### Podman / Dev Containers

`.vscode/settings.json`で、Dev ContainersとContainer Toolsが使用するコマンドを`podman`に設定済みです。利用者による設定変更は不要です。

`dev.containers.dockerPath`という設定名にはDev Containersの互換API名が残っていますが、値は`podman`です。Compose関連の設定は使用しません。

ユーザーごとの手動コンテナ名設定も不要です。Dev Containersがワークスペース単位のコンテナ名とイメージ名を管理します。

### 認証設定の仕組み

IAMアクセスキー方式の`AWS_PROFILE`は、共有プロジェクト設定`.claude/settings.json`だけで指定します。Claude Codeは設定ファイルの`env`から`AWS_PROFILE`を利用できるため、同じ値を`.claude/settings.local.json`へ重複して指定する必要はありません。

`.claude/settings.local.json`はAPIキー方式でのみ使用します。このローカル設定は共有設定より優先され、`AWS_BEARER_TOKEN_BEDROCK`をClaude Codeのプロセスへ設定します。認証設定を変更するためのホストでの`export` / `unset`は不要です。

IAMアクセスキー方式で使用するホストの`~/.aws`は、コンテナの`/home/vscode/.aws`にread-onlyでマウントされます。ホストに`~/.aws`がない場合は、Dev Containersがマウント前に空のディレクトリを自動作成します。

旧構成でホストの`~/.aws/credentials`に`AWS_BEARER_TOKEN_BEDROCK = ...`を記載していた場合、その行は削除またはコメントアウトしてください。現在の構成は同ファイルからAPIキーを読み取りません。

APIキーはBedrock専用なので、APIキー方式の確認に`aws sts get-caller-identity`は使用できません。

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

- `.claude/settings.json`: Bedrock有効化、リージョン、モデル、IAMアクセスキー方式のAWSプロファイル
- `.claude/settings.local.json.template`: APIキー方式専用のローカル設定テンプレート（Git管理対象）
- `.claude/settings.local.json`: テンプレートをリネームして使用するAPIキー設定（Git管理外）
- `.devcontainer/devcontainer.json`: `~/.aws`のread-onlyマウントと、マウント元ディレクトリの初期準備

APIキーはローカル設定ファイルから Claude Code のセッションだけに設定されます。ホスト環境からの `AWS_BEARER_TOKEN_BEDROCK` 転送は行いません。


## 参考リンク

- [VS Code: Alternate ways to install Docker (Podman)](https://code.visualstudio.com/remote/advancedcontainers/docker-options)
- [Dev Containers CLI: Change Log](https://github.com/devcontainers/cli/blob/main/CHANGELOG.md)
- [Podman: Volume mount permission denied (SELinux)](https://github.com/containers/podman/blob/main/troubleshooting.md#2-cant-use-volume-mount-get-permission-denied)
- [Dev Container: Using Images and Container Build Files](https://containers.dev/guide/dockerfile)
- [VS Code: Create a Dev Container（再ビルド）](https://code.visualstudio.com/docs/devcontainers/create-dev-container)
- [Claude Code 公式ドキュメント](https://code.claude.com/docs/ja/overview)
- [Claude Code settings](https://code.claude.com/docs/en/configuration)
- [Claude Code on Amazon Bedrock](https://code.claude.com/docs/en/amazon-bedrock)
- [Amazon Bedrock: API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html)
- [Amazon Bedrock: Use an API key](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-use.html)
- [Amazon Bedrock: APIキーの生成・利用権限](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-permissions.html)
- [Amazon Bedrock: APIキーの権限変更例](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-modify.html)
- [AWS Bedrock 対応モデル一覧](https://docs.aws.amazon.com/ja_jp/bedrock/latest/userguide/inference-profiles-support.html)
