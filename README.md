# Claude Code Sample Repository

Claude Code を AWS Bedrock 経由で利用するための標準リポジトリです。開発環境は rootless Podman と VS Code Dev Containers で起動します。Docker、Docker Compose、podman-compose は使用しません。

## 前提

- Linuxホストにrootless Podmanが導入済みであること
- VS Codeに最新安定版のDev Containers拡張機能（内部のDev Containers CLI 0.76.0以降）が導入済みであること
- AWS Login方式を使う場合:
  - AWS Management ConsoleへサインインできるIAMユーザーまたはロールがあること
  - 対象IDにAWS管理ポリシー`SignInLocalDevelopmentAccess`と、後述のBedrockモデル呼び出し権限があること
- Bedrock APIキー方式を使う場合:
  - AWS Management Consoleで生成したlong-term API keyがあること

`aws login`はAWS CLI v2.32.0以降で利用できます。コンテナには対応するAWS CLI v2を導入し、実行時にもスクリプトでバージョンを確認します。

Dev ContainersのPodman互換性はPodman 5以降が公式の目安です。社内標準環境で別バージョンを使う場合は、後述の構成確認が成功することを確認してください。ComposeプロバイダーとPodman APIソケットの設定は、この構成では参照されません。

## 利用手順

### 1. Dev Containerを起動する

1. このリポジトリをクローンします。
2. VS Codeでリポジトリを開きます。
3. `Dev Containers: Reopen in Container`を実行します。

クローン直後は既存コンテナがないため、`Reopen in Container`でイメージのビルドとコンテナの作成まで実行されます。

以前のリポジトリ構成ですでにDev Containerを作成済みの場合や、`.devcontainer/Containerfile`または`.devcontainer/devcontainer.json`の更新を取得した場合は、古いイメージやコンテナ設定を使わないよう、`Dev Containers: Rebuild and Reopen in Container`を実行してください。特にアクセスキー方式からAWS Login方式へ移行する初回は、AWS認証情報のマウント方式が変わるため再ビルドが必要です。

### 2. Bedrockの認証方式を選ぶ

#### A. AWS Loginを使う

AWS Login方式では、`.claude/settings.local.json`を作成しません。以前にAPIキー方式を使用してこのファイルが残っている場合は削除してください。ローカル設定にAPIキーが残っていると、AWS Login方式へ切り替わりません。

コンテナ内のターミナルで次のスクリプトを実行します。

```bash
./.devcontainer/aws-login.sh
```

スクリプトに表示されたURL（"Please visit the following URL..."に続くもの）をブラウザで開き、使用するIAMユーザーでサインインの後、表示された認証コードをターミナルへ入力します。Dev Container内ではlocalhostコールバックを利用しにくいため、スクリプトは`aws login --remote`を使用します。

ログインに成功すると、次の処理が行われます。

1. AWS Login用プロファイル`bedrock-login`へ最大12時間有効なセッションを作成する
2. ログイン先が期待するAWSアカウント`013958956098`であることを確認する
3. Claude Codeが使用する`bedrock`プロファイルを、`bedrock-login`から一時認証情報を取得する`credential_process`として構成する
4. `bedrock`プロファイルで`sts:GetCallerIdentity`が成功することを確認する

ログイン状態は次のコマンドでも確認できます。

```bash
aws sts get-caller-identity --profile bedrock
```

セッションが失効した場合は、`./.devcontainer/aws-login.sh`を再実行します。

AWS Loginを行うIAMユーザーまたはロールには、AWS管理ポリシー`SignInLocalDevelopmentAccess`に加えて、このリポジトリで指定している推論プロファイルへの次の権限が必要です。

- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`
- `bedrock:ListInferenceProfiles`
- `bedrock:GetInferenceProfile`

#### B. Bedrock APIキーを使う（long-term）

クローン直後には`.claude/settings.local.json`は存在しません。次のコマンドでAPIキー専用テンプレートを`.claude/settings.local.json`へコピーし、所有者だけが読み書きできる権限に変更します。Git管理対象のテンプレートは、認証方式を再度切り替えるときに再利用できるよう残します。

```bash
cp .claude/settings.local.json.template .claude/settings.local.json
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

APIキーに関連付けられたIAMユーザーには、APIキーの使用を許可する`bedrock:CallWithBearerToken`と、Aに記載したBedrockモデル呼び出し権限が必要です。long-term API keyだけに限定する場合は、次のポリシー文をIAMユーザーへ追加します。

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

`bedrock:CallWithBearerToken`の403が表示された場合は、コンテナやAPIキーの読込みではなく、APIキーに関連付けられたIAMユーザーの権限不足です。エラーに`Please run /login`と表示されても、Bedrock APIキー認証はClaude Codeの`/login`では解決しません。上記ポリシーを確認してください。OrganizationsのSCP、permissions boundary、または明示的なDenyがある場合は、Allowを追加しても拒否されるため、管理者による確認が必要です。

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

### AWS Loginの仕組みとセキュリティ

AWS Loginの設定とキャッシュは、ホストの`~/.aws`ではなく、`${devcontainerId}-aws-login`というPodman Named Volumeへ保存します。ホストのAWS設定をコンテナへ公開せず、異なるワークスペース間でも認証情報を分離しながら、コンテナ再ビルド後もログイン状態を再利用できます。ディレクトリ権限は`700`に設定します。

`.claude/settings.json`の`AWS_PROFILE`は`bedrock`です。AWS Loginを直接保存する`bedrock-login`とは分離し、`bedrock`の`credential_process`がAWS CLIの`export-credentials`を呼び出します。これにより、Claude Code側のSDKがAWS Login認証情報を直接扱えない場合も、一時認証情報を標準形式で取得できます。

提示された`allowed_identities`によるユーザー・ロール単位の許可リストは採用していません。この検査を削除してもAWS Loginと`credential_process`は機能し、利用可否はIAMポリシーで制御されます。一方、誤ったアカウントへのログインを防ぐため、変更頻度の低いAWSアカウントIDだけをスクリプトで検査します。アカウントが一致しない場合はログアウトして終了し、`bedrock`プロファイルを書き換えません。

ログアウトする場合は、次のコマンドを実行します。

```bash
aws logout --profile bedrock-login
```

旧アクセスキーはこのNamed Volumeへコピーされません。社内規定に従い、IAM側で旧アクセスキーを無効化・削除し、ホストの`~/.aws/credentials`に残っている固定アクセスキーも別途削除してください。リポジトリからホストの認証情報を自動削除することはありません。

### Bedrock APIキーの仕組み

`.claude/settings.local.json`はAPIキー方式でのみ使用します。このローカル設定は共有設定より優先され、`AWS_BEARER_TOKEN_BEDROCK`をClaude Codeのプロセスへ設定します。APIキー方式ではAWS Loginスクリプトの実行は不要です。

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
- `label=disable` により、SELinuxが有効なホストでもワークスペースのbind mountを利用できます。一方で、このコンテナに対するSELinuxのラベル分離は無効になるため、信頼できるリポジトリだけを開き、追加の機密ディレクトリを安易にマウントしないでください。AWS Loginの設定とキャッシュには、ホストのディレクトリではなくPodman Named Volumeを使用します。
- Dev ContainersからPodmanのbuild/create/start/execを直接使用し、ComposeとPodman APIソケットは使用しません。
- ビルド定義はOCI互換の `.devcontainer/Containerfile` です。
- 外部のベースイメージは `mcr.microsoft.com/...` の完全修飾名を使用します。
- ワークスペースは `/workspace`、実行ユーザーは `vscode` です。
- `dev.containers.dockerPath` と `devcontainer.json` の `build.dockerfile` はDev Containers仕様上の互換名です。実際のコマンドはPodman、実際のファイル名は `Containerfile` です。

## Claude Code / Bedrock の設定

Claude Code の Bedrock 利用設定は `.claude/settings.json` に定義しています。利用モデルやリージョンを変更する場合は、同ファイルの `ANTHROPIC_MODEL`、`ANTHROPIC_SMALL_FAST_MODEL`、`AWS_REGION` を更新します。

認証に関する役割分担は次のとおりです。

- `.claude/settings.json`: Bedrock有効化、リージョン、モデル、AWS Login方式で使用する`bedrock`プロファイル
- `.claude/settings.local.json.template`: APIキー方式専用のローカル設定テンプレート（Git管理対象）
- `.claude/settings.local.json`: テンプレートをコピーして使用するAPIキー設定（Git管理外）
- `.devcontainer/aws-login.sh`: AWSへのremote login、アカウント検査、`credential_process`の構成
- `.devcontainer/devcontainer.json`: Dev Container単位のAWS Login用Named Volumeと権限の設定

APIキーはローカル設定ファイルから Claude Code のセッションだけに設定されます。ホスト環境からの `AWS_BEARER_TOKEN_BEDROCK` 転送は行いません。


## 参考リンク

- [VS Code: Alternate ways to install Docker (Podman)](https://code.visualstudio.com/remote/advancedcontainers/docker-options)
- [VS Code: Improve disk performance（Named Volume）](https://code.visualstudio.com/remote/advancedcontainers/improve-performance)
- [Dev Containers CLI: Change Log](https://github.com/devcontainers/cli/blob/main/CHANGELOG.md)
- [Podman: Volume mount permission denied (SELinux)](https://github.com/containers/podman/blob/main/troubleshooting.md#2-cant-use-volume-mount-get-permission-denied)
- [Dev Container: Using Images and Container Build Files](https://containers.dev/guide/dockerfile)
- [VS Code: Create a Dev Container（再ビルド）](https://code.visualstudio.com/docs/devcontainers/create-dev-container)
- [Claude Code 公式ドキュメント](https://code.claude.com/docs/ja/overview)
- [Claude Code settings](https://code.claude.com/docs/en/configuration)
- [Claude Code on Amazon Bedrock](https://code.claude.com/docs/en/amazon-bedrock)
- [AWS CLI: Sign in with AWS Console credentials](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html)
- [AWS Sign-In: Command line sign-in](https://docs.aws.amazon.com/signin/latest/userguide/command-line-sign-in.html)
- [AWS管理ポリシー: SignInLocalDevelopmentAccess](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/SignInLocalDevelopmentAccess.html)
- [Amazon Bedrock: API keys](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys.html)
- [Amazon Bedrock: Use an API key](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-use.html)
- [Amazon Bedrock: APIキーの生成・利用権限](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-permissions.html)
- [Amazon Bedrock: APIキーの権限変更例](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-modify.html)
- [AWS Bedrock 対応モデル一覧](https://docs.aws.amazon.com/ja_jp/bedrock/latest/userguide/inference-profiles-support.html)
