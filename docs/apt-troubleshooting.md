# APTの障害確認手順

APTの一覧・パッケージ取得でエラーが続く場合は、ビルドログを保存し、実行ホストから取得先までの通信を確認します。現在は通常のDebian公式リポジトリを使用します。リポジトリ側の再試行は断続的な障害を扱いますが、上流の継続的な障害を修復するものではありません。

## 現在の取得先と旧構成からの変更

| 取得先 | suite |
| --- | --- |
| `https://deb.debian.org/debian` | `trixie`、`trixie-updates` |
| `https://deb.debian.org/debian-security` | `trixie-security` |

APTパッケージの14日ルールを解除し、Debian Snapshotへの依存を取り除いています。AWS CLI・Claude Codeにはビルド開始時点の14日ルールを引き続き適用します。TLS証明書検証、Debianの署名検証、メタデータの有効期限チェックは有効です。Snapshot専用のPin-Priorityと`--allow-downgrades`は使用しません。

旧構成ではSnapshotの取得が6回失敗すると停止しました。取得先を変更した現在の構成を反映するには、`Dev Containers: Rebuild and Reopen in Container`を実行します。ログに`APT repositories: debian-current`と上記URLが現れることを確認してください。`APT snapshot:`が現れる場合は、ビルドしたブランチ・ディレクトリと更新の反映を確認します。

既存のプロキシを経由して取得します。今回の切り替えに伴うPC側やPodmanのプロキシ変更は不要です。組織の接続制限で`deb.debian.org:443`が許可されていない環境では、管理者に許可方針を確認します。

## ビルドで行う処理

`.devcontainer/install-apt-packages.sh`は、次の順序で実行します。

| 段階 | 動作 | 失敗時 |
| --- | --- | --- |
| 一覧取得 | `APT::Update::Error-Mode=any`を指定して`update` | 最大6回試行して停止。本体取得には進まない |
| 本体取得 | `install --download-only` | 最大6回試行して停止。インストールには進まない |
| インストール | `install --no-download` | 一度だけ実行し、失敗したら停止 |

APT内部の再試行を0とし、取得段階ごとにスクリプト側で再試行します。待機時間は10・20・30・40・50秒です。各試行ではHTTP(S)の接続・受信タイムアウトを60秒、取得処理全体の上限を300秒とし、終了しない場合は15秒後に強制終了します。タイムアウトは通常124、強制終了時は137として記録されます。これらの取得失敗も上限回数まで再試行します。

一覧取得に失敗した場合、ベースイメージから引き継いだ古い一覧でインストールを続けません。別ホストへの独自のフォールバックや、署名検証・TLS証明書検証の無効化は行いません。

## プロキシの設定元を確認する

Remote-SSHで開いたワークスペースでは、Dev ContainersのビルドコマンドはリモートのLinuxホストで実行されます。PCのWindowsプロキシ設定を切り替えても、Linuxの設定ファイルや既存のVS Code Serverの環境変数は書き換わりません。

`devcontainer.json`は`HTTP_PROXY`・`HTTPS_PROXY`と小文字の同名変数をビルド引数へ渡します。最初にビルドログの`podman ... build`コマンドにある`--build-arg`を確認してください。認証情報を含むプロキシURLは共有前に伏せます。

Linux側では、`/etc/environment`、`/etc/profile.d/`、ユーザーのシェル初期化ファイル、VS Code Serverの起動時環境を管理者が確認します。`NO_PROXY`は接続対象のホストに対する除外設定です。エラーメッセージの`[IP: ... 8080]`はAPTの接続先プロキシを示す場合があり、そのIPだけで504を生成した装置を特定することはできません。

`/etc/apt/apt.conf`・`/etc/apt/apt.conf.d/`の`Acquire::http::Proxy`・`Acquire::https::Proxy`も確認対象です。ホストとコンテナでは設定ファイルが別なので、対象の環境を明確にして確認します。

## 保存する情報

- ビルドを実行したホスト、OS、Podmanのバージョン、rootlessの有無。
- リポジトリのcommitと未commitの変更差分、使用したベースイメージのIDまたはdigest。
- ビルドログ全体。`APT repositories:`、取得先の設定、`build resolution:`、各取得段階のUTC時刻・試行回数・終了コードを含める。
- 失敗した完全なURLとHTTPステータス、発生時刻。日本時間で共有するときはJSTであることを明記する。
- CONNECT応答と、その後のHTTP応答ヘッダー。`server`、`via`、`X-Cache`、`X-Served-By`、`X-Timer`、`Date`、`Location`がある場合は保存する。

ビルドが成功した場合は、イメージ内の以下のファイルも記録します。

```text
/usr/local/share/devcontainer/resolved-releases.json
/usr/local/share/devcontainer/apt-packages.txt
/usr/local/share/devcontainer/apt-sources.sources
```

`resolved-releases.json`の`schema_version`は`2`です。`minimum_age_applies_to`は`aws_cli`と`claude_code`のみ、`apt.minimum_age_seconds`は`null`（待機期間なし）と記録されます。APTの実際の取得先は`apt-sources.sources`、明示的に指定したパッケージの実導入版は`apt-packages.txt`で確認します。SnapshotのURLや指定時刻は現行の監査記録に含めません。

## 実行ホストから応答を採取する

以下はLinuxホストで実行する例です。`target_url`をビルドログで失敗した完全なURLへ置き換えます。既存のプロキシ環境変数を使い、証明書検証を有効にしたまま確認します。

```bash
target_url=https://deb.debian.org/debian-security/dists/trixie-security/InRelease
report_directory=$(mktemp -d /tmp/debian-apt-check.XXXXXX)
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$report_directory/request-start.txt"

curl --http1.1 --fail-with-body --location \
  --connect-timeout 10 --max-time 60 --proto '=https' \
  --dump-header "$report_directory/headers.txt" \
  --output "$report_directory/body" \
  --write-out 'http_code=%{http_code}\nconnect_code=%{http_connect}\nremote_ip=%{remote_ip}\nssl_verify_result=%{ssl_verify_result}\ntime_connect=%{time_connect}\ntime_starttransfer=%{time_starttransfer}\ntime_total=%{time_total}\nurl_effective=%{url_effective}\n' \
  "$target_url" \
  > "$report_directory/metrics.txt"

printf 'Saved response to %s\n' "$report_directory"
```

HTTPエラーではcurlも非0で終了します。保存した`headers.txt`・`metrics.txt`・`request-start.txt`を確認します。CONNECTの200と、その後の取得の503・504は別の応答です。CONNECTと証明書検証が成功している場合、単純なプロキシ接続拒否や証明書検証エラーと区別できます。

`InRelease`だけ成功してもビルドに必要な取得全体が成功したとは限りません。失敗した`Packages.xz`などの圧縮一覧と、実際の`.deb`のURLについても同様に記録します。APTの最終エラーに表示される非圧縮`Packages`は、圧縮一覧の取得失敗後のフォールバック先の場合があります。そのURLだけの404から設定誤りと判断せず、ビルドログも照合してください。

## 管理者に依頼する確認

| 確認対象 | 確認内容 |
| --- | --- |
| 実際の通信経路 | Linuxホストのプロキシ設定、コンテナに渡された引数、接続先が想定どおりか。PC側の切り替えで比較したと判断しない |
| 社内プロキシ | 指定時刻の`CONNECT deb.debian.org:443`と実際のリダイレクト先のアクセスログ、接続エラー、切断、タイムアウト、接続制限を確認。暗号化トンネルだけを扱う場合、内部のURLやHTTPステータスがログに見えない点を考慮する |
| TLS | CONNECTの成否、証明書の検証結果、TLS検査の有無と証明書配布方針を確認。検証無効化で回避しない |
| CDN・上流応答 | クライアントが受け取った503・504のヘッダーと時刻を照合。`X-Cache: MISS`だけで障害箇所を断定せず、必要ならDebianの配布サービス運用側へ照会する |
| 必要な全ファイル | `debian`のTrixie・Trixie Updates、`debian-security`のTrixie Securityについて、署名付きメタデータ、圧縮一覧、`.deb`、リダイレクト先の取得を確認する |
| 継続的な提供方法 | 障害が続く場合、承認されたDebianミラー、署名付きメタデータと本体を保持する社内ミラー、または検証済みOCIイメージの社内配布を検討する |

HTTPSのCONNECTを通すプロキシを追加するだけでは、暗号化されたパッケージ内容のキャッシュができるとは限りません。社内ミラー・イメージ配布を採用する場合は、署名検証、メタデータの有効期限、AWS CLI・Claude Codeの14日の待機期間、更新周期、使用するイメージdigestを運用として明確にします。イメージ配布は「利用者のビルドごとにツールの最新の14日経過版を選ぶ」現行運用も変更します。

代替ホストは、実際のホスト・プロキシ経由で動作と利用可否を確認してから採用します。取得先ホストを変更するときは、Trixieの3系統の提供、署名鍵、有効期限、監査記録の整合性も併せてレビューします。

## 復旧の確認

同じビルドで3系統の一覧取得、必要な本体取得、インストール、AWS CLI・Claude Codeの署名・ハッシュ・バージョン検証がすべて成功し、最終イメージが作成されることを確認します。その後、VS Codeの`Dev Containers: Rebuild and Reopen in Container`で起動を確認します。

リポジトリのテストは次のコマンドで実行できます。追加テストはAPTを模擬して失敗・停止を注入するため、ホストのAPTやインストール済みパッケージを変更しません。

```bash
python3 -m unittest discover -s .devcontainer/tests -v
```

## 公式資料

- [APT: error-on、download-only、no-download](https://manpages.debian.org/trixie/apt/apt-get.8.en.html)
- [APT: HTTPのタイムアウト・プロキシ](https://manpages.debian.org/trixie/apt/apt-transport-http.1.en.html)
- [Debian公式CDNミラー](https://deb.debian.org/)
- [APTの取得先設定・署名鍵・有効期限](https://manpages.debian.org/trixie/apt/sources.list.5.en.html)
- [VS Code Remote-SSH](https://code.visualstudio.com/docs/remote/ssh)
