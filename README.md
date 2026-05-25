# Claude Code Sample Repository

このリポジトリはClaude Codeを使用するためのサンプルプロジェクトです。\
生成AI APIは基盤技術Tが配備したAWSのbedrockを利用します。

## Claude Codeについて

Claude CodeはAnthropic社が提供するAIアシスタント「Claude」のCLIツールです。コードの作成、編集、デバッグ、リファクタリングなど、様々なプログラミングタスクを支援します。

## 使い方

1. このリポジトリをクローン
2. ホスト側の `~/.aws/credentials` に Bedrock 用の AWS 認証情報を設定
3. `devcontainer.json` のコンテナ名を自分の名前など一意なものに変更
4. 必要に応じてsettings.jsonを以下の通りに変更
```
{
  "effortLevel": "high",
  "env": {
    "CLAUDE_CODE_USE_BEDROCK": "1",
    "AWS_REGION": "ap-northeast-1",
    "AWS_PROFILE": "bedrock",  //.aws/credentialsにてこのプロファイル名を指定
    "ANTHROPIC_MODEL": "arn:aws:bedrock:ap-northeast-1:013958956098:inference-profile/<claude-model-id>",  //<claude-model-id>には使用したいモデルのIDを記載 Ex. global.anthropic.claude-sonnet-4-6
    "ANTHROPIC_SMALL_FAST_MODEL": "arn:aws:bedrock:ap-northeast-1:013958956098:inference-profile/<claude-fast-model-id>"  //# <claude-fast-model-id>には使用したい軽量モデルのIDを記載 Ex. global.anthropic.claude-haiku-4-5-20251001-v1:0
  }
}
```
5. devcontainerを展開（VSCodeでreopen in container）
6. ターミナルに"claude"を入力（claude codeを展開）

Claude Code の Bedrock 利用設定は `.claude/settings.json` に定義しています。
`AWS_PROFILE` はデフォルトで `bedrock` を参照するため、`~/.aws/credentials` には以下のようなプロファイルを用意してください。

```
[bedrock]
aws_access_key_id=...
aws_secret_access_key=...
```

別のプロファイル名を使う場合は、`.claude/settings.json` の `AWS_PROFILE` を変更してください。

## 機能

- コード生成と編集
- バグ修正とデバッグ支援
- リファクタリング
- テスト作成
- ドキュメント生成

## ENEOS社内LAN経由での接続について

※現在スパコン構成の変更によりオンプレでは適応不可、EC2では使用可能
※この機能が特に不要で、かつ”Unable to connect to API (ConnectionRefused)”というエラーが出る場合は、「"containerEnv": {"no_proxy": ~~~~~~},」の部分を削除すればClaudeCodeは問題無く使用できる \
devcontainer.json内の"containerEnv"にてBedrockに対してno_proxy設定をしており、
外部インターネットを経由しない閉域ルート（社内LAN->DirectConnect->Bedrock）での接続が可能です。
適切に接続されているかは以下コマンドで確認。

```
echo $no_proxy
```
bedrock.ap-northeast-1.amazonaws.com,bedrock-runtime.ap-northeast-1.amazonaws.com
```
curl -v https://bedrock-runtime.ap-northeast-1.amazonaws.com
```
* Uses proxy env variable no_proxy == 'bedrock.ap-northeast-1.amazonaws.com,bedrock-runtime.ap-northeast-1.amazonaws.com'
*   Trying 10.81.16.181:443...
* Connected to bedrock-runtime.ap-northeast-1.amazonaws.com (10.81.16.181) port 443 (#0)


## 参考リンク

- [Claude Code 公式ドキュメント](https://code.claude.com/docs/ja/overview)
- [AWS Bedrock 対応モデル一覧](https://docs.aws.amazon.com/ja_jp/bedrock/latest/userguide/inference-profiles-support.html)
※プロンプトデータを国内に留めておきたい特別な事情が無い限り、"global.~~"のモデルでok
