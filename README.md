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

Dev ContainerのOSはDebian 12 Bookwormです。BullseyeはEOLのため使用しません。

Dev ContainersのPodman互換性はPodman 5以降が公式の目安です。社内標準環境で別バージョンを使う場合は、後述の構成確認が成功することを確認してください。ComposeプロバイダーとPodman APIソケットの設定は、この構成では参照されません。

## 利用手順

### 1. Dev Containerを起動する

1. このリポジトリをクローンします。
2. VS Codeでリポジトリを開きます。
3. `Dev Containers: Reopen in Container`を実行します。

起動処理はビルド直前のUTC時刻を生成し、その時点で公開から14日以上経過したAWS CLI・Claude Codeを毎回選び直します。APTパッケージは、14日の待機期間を設けず、通常のDebian公式リポジトリからBookworm向けの候補版を取得します。初回ビルドと再ビルドにはGitHub、Debianの`deb.debian.org`、AWS、Anthropic、npm（構成確認用CLIを使う場合）へのネットワーク接続が必要です。ベースイメージが未取得の場合や更新する場合は、Microsoft Container Registryへの接続も必要です。

既存のDev Containerがある状態で`.devcontainer/Containerfile`、`.devcontainer/devcontainer.json`または依存導入スクリプトの更新を取得した場合は、`Dev Containers: Rebuild and Reopen in Container`を実行します。

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

値には、Bedrockの基盤モデルID、クロスリージョン推論プロファイルID、または推論プロファイルARNを指定します。このリポジトリの共有設定では、AWSアカウントIDを含まないシステム定義の推論プロファイルIDを使用しています。選択したモデルまたは推論プロファイルが`AWS_REGION`から呼び出せること、使用するAWSアカウントでアクセスできること、IAMポリシーで呼び出しが許可されていることを確認してください。

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

別のAWSアカウントを使用する場合は、`.claude/settings.json`の`ANTHROPIC_MODEL`と`ANTHROPIC_DEFAULT_HAIKU_MODEL`が、そのアカウントと`AWS_REGION`で利用できることを確認します。利用できない場合は、両方を利用可能なモデルID、推論プロファイルID、または選択したアカウントのARNへ変更してください。ARNを使用する場合は、元のアカウントIDが残っていないことも確認します。

利用者単位でAWSアカウントを切り替える場合は、共有の`.claude/settings.json`を変更せず、Git管理外の`.claude/settings.local.json`でプロファイル名と両方のモデルを上書きできます。

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "env": {
    "AWS_PROFILE": "my-bedrock",
    "ANTHROPIC_MODEL": "MODEL_OR_INFERENCE_PROFILE_FOR_SELECTED_ACCOUNT",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "HAIKU_MODEL_OR_INFERENCE_PROFILE_FOR_SELECTED_ACCOUNT"
  }
}
```

続いて、誤ログイン検知が正しく働くよう、選択したAWSアカウントの12桁のアカウントIDを`EXPECTED_AWS_ACCOUNT_ID`へ指定します。

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
./.devcontainer/devcontainer-cli.sh up \
  --workspace-folder . \
  --docker-path podman \
  --buildkit never
```

起動後はPodmanがコンテナを管理していることを確認できます。

```bash
podman ps
```

コンテナ内では、OS、ツール、ワークスペースを次のように確認できます。

```bash
cat /etc/os-release
python --version
aws --version
claude --version
cat /usr/local/share/devcontainer/resolved-releases.json
cat /usr/local/share/devcontainer/apt-packages.txt
cat /usr/local/share/devcontainer/apt-sources.sources
pwd
ls -la /workspace
findmnt /workspace
```

`VERSION_ID="12"`、`VERSION_CODENAME=bookworm`、作業ディレクトリが`/workspace`となり、同ディレクトリにこのリポジトリの内容が表示されれば正常です。`/workspace`が空の場合は、まずPodman 5以降で再現するか確認し、`podman inspect <container-id>`の`Mounts`でホストのリポジトリが`/workspace`へbind mountされているか確認してください。

### 依存バージョンの動的選定方針

Dev Container内へ明示的に導入するAPTパッケージ、AWS CLI、Claude Codeは、バージョンをリポジトリへ固定していません。AWS CLIとClaude Codeは、ユーザーがビルドを開始するたび、次の手順で「公開から14日以上（336時間）経過した中で最も新しい安定版」を選びます。APTパッケージにはこの待機期間を適用しません。

1. `initializeCommand`がホスト上でビルド開始時刻をUTC秒単位で生成する
2. その時刻ファイルをContainerfileの入力にして、過去の依存導入レイヤーのキャッシュを無効化する
3. ビルド開始時刻から正確に`14 * 24 * 60 * 60`秒を引いた時刻をカットオフとする
4. 各配布元に合った方法で候補を選び、検証に成功した配布物だけをインストールする

対象ごとの判定方法は次のとおりです。

- Debian APT: `https://deb.debian.org/debian`の`bookworm`・`bookworm-updates`と、`https://deb.debian.org/debian-security`の`bookworm-security`を使用します。14日の待機期間は設けず、取得した一覧に基づくAPTの通常の候補選定で、指定パッケージと必要な依存をインストールします。OS系列はBookwormのままです。ベースイメージ内の全パッケージを一括更新する処理ではありません。Debianの署名検証、TLS証明書検証、メタデータの有効期限チェックは有効にし、Snapshot用の優先度設定や強制ダウングレードは使用しません。
- AWS CLI v2: AWS公式リポジトリの全履歴を含むCHANGELOGから候補版を列挙し、対象アーキテクチャの公式配布ZIPに付く`Last-Modified`がカットオフ以前の中で最も新しいSemVerを選びます。ZIPはAWS CLI TeamのPGP署名を検証し、実際に署名した鍵のprimary fingerprintが公式値と一致することも確認します。
- Claude Code: Anthropic公式GitHub Releasesを最終ページまで取得し、`published_at`がカットオフ以前で、draftでもprereleaseでもない全候補から最も新しいSemVerを選びます。Anthropicの署名済み`manifest.json`について、鍵ファイルに公式primary fingerprint以外が含まれないことと実際の署名者がその鍵であることを検証し、その中のSHA-256とファイルサイズが一致するLinuxバイナリだけを導入します。
- Dev Containers CLI: 下記の構成確認用ラッパーはnpmの公開時刻から同じ14日ルールを満たす版を選びます。VS Code拡張機能に内蔵されたCLIは拡張機能側で管理され、コンテナへ導入する依存には含みません。

`mcr.microsoft.com/devcontainers/python:3.12-bookworm`は、Python 3.12とBookwormという互換性系列だけを指定するフローティングタグです。Containerfile実行前に必要となるブートストラップイメージのため、上記リゾルバーの対象外です。

同じcommitでもビルド時点の配布状況が変われば、導入版が変わる可能性があります。監査用に次の3ファイルをイメージ内へ保存します。

- `/usr/local/share/devcontainer/resolved-releases.json`: AWS CLI・Claude Codeの選定時刻、カットオフ、公開時刻または配布物の更新時刻、導入版、取得URL。`schema_version`は`2`で、`minimum_age_applies_to`に14日ルールの対象を明示します。`apt.repository_mode`は`debian-current`、`apt.minimum_age_seconds`は`null`（待機期間なし）です。旧`debian_snapshot`フィールドは出力しません。
- `/usr/local/share/devcontainer/apt-packages.txt`: 明示的に指定したAPTパッケージの実導入版。
- `/usr/local/share/devcontainer/apt-sources.sources`: ビルドで実際に使用したAPT取得先の設定。旧`apt-snapshot-timestamp.txt`を置き換えます。

申請・監査では、この3ファイルとベースイメージ・完成イメージのdigestを一緒に記録してください。通常のミラーは配布内容が更新されるため、これらの記録だけでは同一イメージの再ビルドを保証できません。同一環境を再利用する必要がある場合は、完成イメージを保持してdigestで指定します。

公開情報の取得、14日以上経過した候補の発見、fingerprint、PGP署名、checksum、ファイルサイズ、または導入後のバージョン確認のどれかに失敗した場合、別版へ無条件にフォールバックせずビルドを停止します。Claude Codeの自動更新と手動更新も共有設定で停止し、版の更新は次回のDev Container rebuildだけで行います。

### APTの取得失敗と長時間待機への対応

Debian Snapshotで503・504が継続する問題を受け、APTの取得先を通常のDebian公式リポジトリへ変更しました。APTに限って14日ルールを解除しており、AWS CLI・Claude Codeの選定・署名検証と既存のプロキシ設定は維持します。更新後は`Dev Containers: Rebuild and Reopen in Container`を実行してください。

APTの一覧取得とパッケージ本体のダウンロードは、各段階で最大6回（初回1回＋再試行5回）実行します。再試行前の待機は10・20・30・40・50秒です。APT内部の`Acquire::Retries`は0とし、503・504も含めてスクリプト側で処理全体を再試行します。

一覧取得は`APT::Update::Error-Mode=any`で一時的なエラーも失敗として扱います。ベースイメージの古い一覧を削除してから取得し、成功するまで次の段階へ進みません。パッケージ本体は`--download-only`で先に揃え、成功後に`--no-download`でインストールします。dpkgによるインストール自体は一度だけ実行し、失敗を再試行で隠しません。

HTTP(S)の接続・受信タイムアウトは60秒です。別途、各取得処理全体を300秒で打ち切り、終了しない場合は15秒後に強制終了します。上限は取得1回に対するもので、ビルド全体やdpkgの実行時間の上限ではありません。ビルドログにはAPTの取得先、ビルド開始時刻、取得段階、UTC時刻、試行回数と終了コードを表示します。

この対策は断続的な障害への再試行と、取得が完了しない場合の停止を行います。通常のDebianミラーや通信経路の障害が継続すればビルドは失敗します。管理者への共有事項とログの採取方法は[APTの障害確認手順](docs/apt-troubleshooting.md)を参照してください。Remote-SSHでビルドする場合、ビルドが参照するのはLinuxホスト側のプロキシ環境変数です。

### Podman 運用方針

- `privileged` は使用しません。
- rootless Podmanを使用します。Linux版のDev Containers CLIはPodman利用時に `--security-opt label=disable` と、非rootユーザーに対する `--userns=keep-id` を自動付与します。そのため、同じオプションを `runArgs` へ重複して定義しません。
- `label=disable` により、SELinuxが有効なホストでもワークスペースのbind mountを利用できます。一方で、このコンテナに対するSELinuxのラベル分離は無効になるため、信頼できるリポジトリだけを開き、追加の機密ディレクトリを安易にマウントしないでください。AWS Loginの設定とキャッシュには、ホストのディレクトリではなくPodman Named Volumeを使用します。
- Dev ContainersからPodmanのbuild/create/start/execを直接使用し、ComposeとPodman APIソケットは使用しません。
- ビルド定義はOCI互換の `.devcontainer/Containerfile` です。
- 外部のベースイメージは`mcr.microsoft.com/...`の完全修飾名とBookwormのフローティングタグを使用します。
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
- [Dev Container specification: initializeCommand](https://github.com/devcontainers/spec/blob/main/docs/specs/devcontainerjson-reference.md#lifecycle-scripts)
- [Debian公式CDNミラー](https://deb.debian.org/)
- [APTの取得先設定・署名鍵・有効期限](https://manpages.debian.org/bookworm/apt/sources.list.5.en.html)
- [AWS CLI installation and PGP verification](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
- [GitHub REST API: Releases](https://docs.github.com/en/rest/releases/releases)
- [Claude Code version management and binary integrity](https://code.claude.com/docs/en/setup)
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
