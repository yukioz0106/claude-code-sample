# Debian Snapshotの障害確認手順

Debian Snapshotの一覧・パッケージ取得で503・504が続く場合は、ビルドログを保存し、実行ホストからSnapshotまでの通信を確認します。リポジトリ側の再試行は断続的な障害を扱いますが、上流の継続的な障害を修復するものではありません。

## ビルドで行う処理

`.devcontainer/install-apt-packages.sh`は、次の順序で実行します。

| 段階 | 動作 | 失敗時 |
| --- | --- | --- |
| 一覧取得 | `APT::Update::Error-Mode=any`を指定して`update` | 最大6回試行して停止。本体取得には進まない |
| 本体取得 | `install --download-only` | 最大6回試行して停止。インストールには進まない |
| インストール | `install --no-download` | 一度だけ実行し、失敗したら停止 |

APT内部の再試行を0とし、取得段階ごとにスクリプト側で再試行します。待機時間は10・20・30・40・50秒です。各試行ではHTTP(S)の接続・受信タイムアウトを60秒、取得処理全体の上限を300秒とし、終了しない場合は15秒後に強制終了します。タイムアウトは通常124、強制終了時は137として記録されます。これらの取得失敗も上限回数まで再試行します。

Snapshotの指定時刻はビルド開始から正確に14日前です。時間単位への丸めは行いません。一般のDebianミラーへの自動切り替え、署名検証・TLS証明書検証の無効化は行いません。

## プロキシの設定元を確認する

Remote-SSHで開いたワークスペースでは、Dev ContainersのビルドコマンドはリモートのLinuxホストで実行されます。PCのWindowsプロキシ設定を切り替えても、Linuxの設定ファイルや既存のVS Code Serverの環境変数は書き換わりません。

`devcontainer.json`は`HTTP_PROXY`・`HTTPS_PROXY`と小文字の同名変数をビルド引数へ渡します。最初にビルドログの`podman ... build`コマンドにある`--build-arg`を確認してください。認証情報を含むプロキシURLは共有前に伏せます。

Linux側では、`/etc/environment`、`/etc/profile.d/`、ユーザーのシェル初期化ファイル、VS Code Serverの起動時環境を管理者が確認します。`NO_PROXY`は接続対象のホストに対する除外設定です。エラーメッセージの`[IP: ... 8080]`はAPTの接続先プロキシを示す場合があり、そのIPだけで504を生成した装置を特定することはできません。

`/etc/apt/apt.conf`・`/etc/apt/apt.conf.d/`の`Acquire::http::Proxy`・`Acquire::https::Proxy`も確認対象です。ホストとコンテナでは設定ファイルが別なので、対象の環境を明確にして確認します。

## 保存する情報

- ビルドを実行したホスト、OS、Podmanのバージョン、rootlessの有無。
- リポジトリのcommitと未commitの変更差分、使用したベースイメージのIDまたはdigest。
- ビルドログ全体。`APT snapshot:`、`build resolution:`、各取得段階のUTC時刻・試行回数・終了コードを含める。
- 失敗した完全なURLとHTTPステータス、発生時刻。日本時間で共有するときはJSTであることを明記する。
- CONNECT応答と、その後のHTTP応答ヘッダー。`server`、`via`、`X-Cache`、`X-Served-By`、`X-Timer`、`Date`、`Location`がある場合は保存する。

ビルドが成功した場合は、イメージ内の以下のファイルも記録します。

```text
/usr/local/share/devcontainer/resolved-releases.json
/usr/local/share/devcontainer/apt-packages.txt
/usr/local/share/devcontainer/apt-snapshot-timestamp.txt
```

## 実行ホストから応答を採取する

以下はLinuxホストで実行する例です。`snapshot_timestamp`をビルドログの値へ置き換えます。既存のプロキシ環境変数を使い、証明書検証を有効にしたまま確認します。

```bash
snapshot_timestamp=20261022T042930Z
report_directory=$(mktemp -d /tmp/debian-snapshot-check.XXXXXX)
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$report_directory/request-start.txt"

curl --http1.1 --fail-with-body --location \
  --connect-timeout 10 --max-time 60 --proto '=https' \
  --dump-header "$report_directory/headers.txt" \
  --output "$report_directory/body" \
  --write-out 'http_code=%{http_code}\nconnect_code=%{http_connect}\nremote_ip=%{remote_ip}\nssl_verify_result=%{ssl_verify_result}\ntime_connect=%{time_connect}\ntime_starttransfer=%{time_starttransfer}\ntime_total=%{time_total}\nurl_effective=%{url_effective}\n' \
  "https://snapshot.debian.org/archive/debian-security/$snapshot_timestamp/dists/bookworm-security/InRelease" \
  > "$report_directory/metrics.txt"

printf 'Saved response to %s\n' "$report_directory"
```

HTTPエラーではcurlも非0で終了します。保存した`headers.txt`・`metrics.txt`・`request-start.txt`を確認します。CONNECTの200と、その後の取得の503・504は別の応答です。CONNECTと証明書検証が成功している場合、単純なプロキシ接続拒否や証明書検証エラーと区別できます。

`InRelease`だけ成功してもビルドに必要な取得全体が成功したとは限りません。失敗した`Packages.xz`などの圧縮一覧と、実際の`.deb`のURLについても同様に記録します。APTの最終エラーに表示される非圧縮`Packages`は、圧縮一覧の取得失敗後のフォールバック先の場合があります。そのURLだけの404から設定誤りと判断せず、ビルドログも照合してください。

## 管理者に依頼する確認

| 確認対象 | 確認内容 |
| --- | --- |
| 実際の通信経路 | Linuxホストのプロキシ設定、コンテナに渡された引数、接続先が想定どおりか。PC側の切り替えで比較したと判断しない |
| 社内プロキシ | 指定時刻の`CONNECT snapshot.debian.org:443`のアクセスログ、接続エラー、切断、タイムアウト、接続制限を確認。暗号化トンネルだけを扱う場合、内部のURLやHTTPステータスがログに見えない点を考慮する |
| TLS | CONNECTの成否、証明書の検証結果、TLS検査の有無と証明書配布方針を確認。検証無効化で回避しない |
| CDN・上流応答 | クライアントが受け取った503・504のヘッダーと時刻を照合。`X-Cache: MISS`だけで障害箇所を断定せず、必要ならDebian Snapshot運用側へ照会する |
| 必要な全ファイル | `debian`のBookworm・Bookworm Updates、`debian-security`のBookworm Securityについて、署名付きメタデータ、圧縮一覧、`.deb`、リダイレクト先の取得を確認する |
| 継続的な提供方法 | 障害が続く場合、承認されたSnapshotミラー、署名付きメタデータと本体を保持する社内ミラー、または検証済みOCIイメージの社内配布を検討する |

HTTPSのCONNECTを通すプロキシを追加するだけでは、暗号化されたパッケージ内容のキャッシュができるとは限りません。社内ミラー・イメージ配布を採用する場合は、署名検証、Snapshot日時、14日の待機期間、更新周期、使用するイメージdigestを運用として明確にします。イメージ配布は「利用者のビルドごとに最新の14日経過版を選ぶ」現行運用も変更します。

代替ホストは、実際のホスト・プロキシ経由で動作と利用可否を確認してから採用します。取得先ホストを変更するときは、APTの`Pin: origin`と署名鍵・Snapshot日時の扱いも併せてレビューします。

## 復旧の確認

同じビルドで3系統の一覧取得、必要な本体取得、インストール、AWS CLI・Claude Codeの署名・ハッシュ・バージョン検証がすべて成功し、最終イメージが作成されることを確認します。その後、VS Codeの`Dev Containers: Rebuild and Reopen in Container`で起動を確認します。

リポジトリのテストは次のコマンドで実行できます。追加テストはAPTを模擬して失敗・停止を注入するため、ホストのAPTやインストール済みパッケージを変更しません。

```bash
python3 -m unittest discover -s .devcontainer/tests -v
```

## 公式資料

- [APT: error-on、download-only、no-download](https://manpages.debian.org/bookworm/apt/apt-get.8.en.html)
- [APT: HTTPのタイムアウト・プロキシ](https://manpages.debian.org/bookworm/apt/apt-transport-http.1.en.html)
- [Debian Snapshotの利用方法](https://snapshot.debian.org/)
- [VS Code Remote-SSH](https://code.visualstudio.com/docs/remote/ssh)
