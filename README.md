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

既存のDev Containerがある状態で`.devcontainer/Containerfile`または`.devcontainer/devcontainer.json`の更新を取得した場合は、`Dev Containers: Rebuild and Reopen in Container`を実行します。

### 2. 使用するモデルを指定する

AWS Login方式とBedrock APIキー方式のどちらを使う場合も、`.claude/settings.json`を開き、必要に応じて次の値を変更します。

- `AWS_REGION`: Bedrockを呼び出すリージョン
- `ANTHROPIC_MODEL`: メインモデルのモデルID、推論プロファイルIDまたはARN
- `ANTHROPIC_DEFAULT_HAIKU_MODEL`: 軽量処理用モデルのモデルID、推論プロファイルIDまたはARN

利用可能なモデルIDの確認先と確認コマンドは「補足」の「Bedrockモデルの指定と確認」を参照してください。

### 3. Bedrockの認証方式を選ぶ

#### A. AWS Loginを使う

以前にAPIキー方式を使用していた場合は、`.claude/settings.local.json`から`AWS_BEARER_TOKEN_BEDROCK`を削除します。ほかに設定がなければファイル自体を削除します。

既定の`bedrock`プロファイルを使う場合は、コンテナ内で次のコマンドを実行します。

```bash
./.devcontainer/aws-login.sh
```

操作用プロファイルを別名にする場合は、Git管理外の`.claude/settings.local.json`に使用する名前を設定します。

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "env": {
    "AWS_PROFILE": "my-bedrock"
  }
}
```

```bash
OPS_PROFILE=my-bedrock \
AWS_REGION=ap-northeast-1 \
./.devcontainer/aws-login.sh
```

スクリプトに表示されたURLをブラウザで開き、使用するIAMユーザーまたはロールでサインインして、表示された認証コードをターミナルへ入力します。

セッションが失効した場合は、初回と同じ環境変数を指定してスクリプトを再実行します。

#### B. Bedrock APIキーを使う（long-term）

APIキー専用テンプレートを`.claude/settings.local.json`へコピーし、所有者だけが読み書きできる権限に変更します。

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

### 4. Claude Codeを起動する

コンテナ内のターミナルで次のコマンドを実行します。

```bash
claude
```

Claude Codeの`/status`で、プロバイダーがAmazon Bedrockであることと、意図した設定ソースが読み込まれていることを確認します。最終的な疎通は、実際にプロンプトを送信して確認してください。

## 補足

### Dev Containerの起動と設定反映

クローン直後は既存コンテナがないため、`Reopen in Container`でイメージのビルドとコンテナの作成まで実行されます。

以前のリポジトリ構成ですでにDev Containerを作成済みの場合や、`.devcontainer/Containerfile`または`.devcontainer/devcontainer.json`の更新を取得した場合は、古いイメージやコンテナ設定を使わないよう、`Dev Containers: Rebuild and Reopen in Container`を実行してください。特にアクセスキー方式からAWS Login方式へ移行する初回は、AWS認証情報のマウント方式が変わるため再ビルドが必要です。

`.claude/settings.json`または`.claude/settings.local.json`だけを変更した場合は、実行中のClaude Codeを終了して新しく起動すれば反映されます。Dev Containerの再作成は不要です。

### Bedrockモデルの指定と確認

モデルとリージョンは、認証方式にかかわらずGit管理対象の`.claude/settings.json`で指定します。

- `AWS_REGION`: Bedrock APIを呼び出すソースリージョン。このリポジトリの既定値は東京リージョンの`ap-northeast-1`です。
- `ANTHROPIC_MODEL`: Claude Codeが通常の処理に使用するメインモデルです。
- `ANTHROPIC_DEFAULT_HAIKU_MODEL`: セッションタイトル生成などの軽量なバックグラウンド処理に使用するモデルです。旧設定名の`ANTHROPIC_SMALL_FAST_MODEL`は非推奨です。

値には、Bedrockの基盤モデルID、クロスリージョン推論プロファイルID、または推論プロファイルARNを指定します。このリポジトリでは推論プロファイルARNを使用しています。選択したモデルまたは推論プロファイルが`AWS_REGION`から呼び出せること、使用するAWSアカウントでアクセスできること、IAMポリシーで呼び出しが許可されていることを確認してください。

現在利用できるモデルと正確なIDは、AWS公式ドキュメントの[Model availability & compatibility](https://docs.aws.amazon.com/bedrock/latest/userguide/models.html)から対象モデルの詳細ページを開いて確認します。モデルIDの種類ごとの確認先は[Using models with Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/foundation-models-reference.html)、クロスリージョン推論プロファイルIDと利用可能なソース／宛先リージョンは[Supported Regions and models for inference profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html)を参照してください。Claude Code側の指定方法は[Claude Code on Amazon Bedrock](https://code.claude.com/docs/en/amazon-bedrock)で確認できます。

AWS Login完了後は、現在のリージョンから利用できるシステム定義の推論プロファイルをAWS CLIでも確認できます。別名のAWSプロファイルを使用している場合は、`--profile bedrock`をその名前に置き換えます。

```bash
aws bedrock list-inference-profiles \
  --type-equals SYSTEM_DEFINED \
  --region ap-northeast-1 \
  --profile bedrock \
  --query 'inferenceProfileSummaries[].[inferenceProfileId,inferenceProfileArn]' \
  --output table
```

モデルまたはリージョンを変更した場合は、Bedrock呼び出し権限の対象リソースとリージョンも合わせて見直してください。

### AWS Loginのプロファイル、権限、仕組み

操作用の`bedrock`プロファイルやログイン用の`bedrock-login`プロファイルは、事前に作成する必要がありません。`aws-login.sh`がコンテナ内の`~/.aws/config`へ両方のプロファイルを作成または更新します。

既定の名前で実行した場合、`~/.aws/config`は概ね次の構成になります。`login_session`の値は、サインインしたIAMユーザーまたはロールに応じて`aws login`が設定します。

```ini
[profile bedrock-login]
login_session = arn:aws:iam::012345678901:user/example
region = ap-northeast-1

[profile bedrock]
region = ap-northeast-1
output = json
credential_process = aws configure export-credentials --profile bedrock-login --format process
```

`.claude/settings.json`または`.claude/settings.local.json`の`AWS_PROFILE`と、スクリプトの`OPS_PROFILE`は同じ名前にする必要があります。`LOGIN_PROFILE`を省略すると、ログイン用プロファイルは`<OPS_PROFILE>-login`になります。チーム全体で名前を変更する場合は共有の`.claude/settings.json`を、利用者単位で変更する場合はGit管理外の`.claude/settings.local.json`を使用します。

ログイン用プロファイルにも任意の名前を使う場合は、操作用とは異なる名前を`LOGIN_PROFILE`へ指定します。

```bash
OPS_PROFILE=my-bedrock \
LOGIN_PROFILE=my-console-login \
AWS_REGION=ap-northeast-1 \
./.devcontainer/aws-login.sh
```

別のAWSアカウントを使用する場合は、誤ログイン検知が正しく働くよう、12桁のアカウントIDを`EXPECTED_AWS_ACCOUNT_ID`へ指定します。

```bash
OPS_PROFILE=my-bedrock \
EXPECTED_AWS_ACCOUNT_ID=123456789012 \
AWS_REGION=ap-northeast-1 \
./.devcontainer/aws-login.sh
```

スクリプトは`aws login --remote`を実行し、ログイン成功後に次の処理を行います。

1. ログイン用プロファイルへ最大12時間有効なセッションを作成する
2. ログイン先が期待するAWSアカウントであることを確認する
3. 操作用プロファイルを、ログイン用プロファイルから一時認証情報を取得する`credential_process`として構成する
4. 操作用プロファイルで`sts:GetCallerIdentity`が成功することを確認する

ログイン状態は次のコマンドでも確認できます。別名を使用している場合は、`bedrock`を操作用プロファイル名に置き換えます。

```bash
aws sts get-caller-identity --profile bedrock
```

AWS Loginを行うIAMユーザーまたはロールには、AWS管理ポリシー`SignInLocalDevelopmentAccess`に加えて、使用するモデルまたは推論プロファイルへの次の権限が必要です。

- `bedrock:InvokeModel`
- `bedrock:InvokeModelWithResponseStream`
- `bedrock:ListInferenceProfiles`
- `bedrock:GetInferenceProfile`

AWS Loginの設定とキャッシュは、ホストの`~/.aws`ではなく、`${devcontainerId}-aws-login`というPodman Named Volumeへ保存します。ホストのAWS設定をコンテナへ公開せず、異なるワークスペース間でも認証情報を分離しながら、コンテナ再ビルド後もログイン状態を再利用できます。ディレクトリ権限は`700`に設定します。

提示された`allowed_identities`によるユーザー・ロール単位の許可リストは採用していません。利用可否はIAMポリシーで制御し、誤ったアカウントへのログインはAWSアカウントIDの検査で防ぎます。アカウントが一致しない場合はログアウトして終了し、操作用プロファイルを書き換えません。

ログアウトする場合は、ログイン用プロファイルを指定します。

```bash
aws logout --profile bedrock-login
```

旧アクセスキーはNamed Volumeへコピーされません。社内規定に従い、IAM側で旧アクセスキーを無効化・削除し、ホストの`~/.aws/credentials`に残っている固定アクセスキーも別途削除してください。リポジトリからホストの認証情報を自動削除することはありません。

### Bedrock APIキーの権限と仕組み

APIキーに関連付けられたIAMユーザーには、APIキーの使用を許可する`bedrock:CallWithBearerToken`と、前述のBedrockモデル呼び出し権限が必要です。long-term API keyだけに限定する場合は、次のポリシー文をIAMユーザーへ追加します。

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

`bedrock:CallWithBearerToken`の403が表示された場合は、APIキーに関連付けられたIAMユーザーの権限を確認してください。エラーに`Please run /login`と表示されても、Bedrock APIキー認証はClaude Codeの`/login`では解決しません。OrganizationsのSCP、permissions boundary、または明示的なDenyがある場合は、Allowを追加しても拒否されるため、管理者による確認が必要です。

`.claude/settings.local.json`は、APIキーまたは利用者固有のAWSプロファイル名を保存するために使用します。APIキー方式では、共有設定より優先して`AWS_BEARER_TOKEN_BEDROCK`をClaude Codeのプロセスへ設定します。AWS Loginスクリプトの実行は不要です。

旧構成でホストの`~/.aws/credentials`に`AWS_BEARER_TOKEN_BEDROCK = ...`を記載していた場合、その行は削除またはコメントアウトしてください。現在の構成は同ファイルからAPIキーを読み取りません。

APIキーはBedrock専用なので、APIキー方式の確認に`aws sts get-caller-identity`は使用できません。

> [!NOTE]
> AWSはlong-term API keyを検証・探索用途向けと位置づけ、本番用途にはshort-term API keyを推奨しています。本構成はlong-term API keyに対応しますが、キーには有効期限と必要最小限の権限を設定してください。

### Podman / Dev Containers

`.vscode/settings.json`で、Dev ContainersとContainer Toolsが使用するコマンドを`podman`に設定済みです。利用者による設定変更は不要です。

`dev.containers.dockerPath`という設定名にはDev Containersの互換API名が残っていますが、値は`podman`です。Compose関連の設定は使用しません。

ユーザーごとの手動コンテナ名設定も不要です。Dev Containersがワークスペース単位のコンテナ名とイメージ名を管理します。

### 構成の確認

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

### Podman 運用方針

- `privileged` は使用しません。
- rootless Podmanを使用します。Linux版のDev Containers CLIはPodman利用時に `--security-opt label=disable` と、非rootユーザーに対する `--userns=keep-id` を自動付与します。そのため、同じオプションを `runArgs` へ重複して定義しません。
- `label=disable` により、SELinuxが有効なホストでもワークスペースのbind mountを利用できます。一方で、このコンテナに対するSELinuxのラベル分離は無効になるため、信頼できるリポジトリだけを開き、追加の機密ディレクトリを安易にマウントしないでください。AWS Loginの設定とキャッシュには、ホストのディレクトリではなくPodman Named Volumeを使用します。
- Dev ContainersからPodmanのbuild/create/start/execを直接使用し、ComposeとPodman APIソケットは使用しません。
- ビルド定義はOCI互換の `.devcontainer/Containerfile` です。
- 外部のベースイメージは `mcr.microsoft.com/...` の完全修飾名を使用します。
- ワークスペースは `/workspace`、実行ユーザーは `vscode` です。
- `dev.containers.dockerPath` と `devcontainer.json` の `build.dockerfile` はDev Containers仕様上の互換名です。実際のコマンドはPodman、実際のファイル名は `Containerfile` です。

### Claude Code / Bedrock の設定

Claude Code の Bedrock 利用設定は `.claude/settings.json` に定義しています。利用モデルやリージョンを変更する場合は、同ファイルの `ANTHROPIC_MODEL`、`ANTHROPIC_DEFAULT_HAIKU_MODEL`、`AWS_REGION` を更新します。

認証に関する役割分担は次のとおりです。

- `.claude/settings.json`: Bedrock有効化、リージョン、モデル、AWS Login方式で使用する`bedrock`プロファイル
- `.claude/settings.local.json.template`: APIキー方式専用のローカル設定テンプレート（Git管理対象）
- `.claude/settings.local.json`: APIキーまたは利用者固有のAWSプロファイル名（Git管理外）
- `.devcontainer/aws-login.sh`: AWSへのremote login、アカウント検査、`credential_process`の構成
- `.devcontainer/devcontainer.json`: Dev Container単位のAWS Login用Named Volumeと権限の設定

APIキーはローカル設定ファイルから Claude Code のセッションだけに設定されます。ホスト環境からの `AWS_BEARER_TOKEN_BEDROCK` 転送は行いません。


### 参考リンク

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
