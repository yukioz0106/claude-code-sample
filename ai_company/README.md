# ai_company — Lumina Works（AI組織シミュレーション）

Claude Codeのカスタムサブエージェントを使って、架空の小規模ソフトウェア会社「Lumina Works」を再現したものです。CEO 1名 + 部門リーダー4名の体制で、依頼内容をCEOが各部門に割り振り、成果物を統合して報告する、という組織の動き方をシミュレーションします。

## 構成

```
ai_company/
  CHARTER.md              会社憲章（ミッション・事業内容・組織規模）
  org-chart.md            組織図、エージェント対応表、意思決定フロー
  departments/
    engineering.md         Engineering部門の責務
    design.md               Design部門の責務
    marketing.md             Marketing部門の責務
    sales.md                  Sales/BizDev部門の責務
  processes/
    task-intake.md          タスクの依頼フロー

.claude/agents/
  lumina-ceo.md
  lumina-eng-lead.md
  lumina-design-lead.md
  lumina-marketing-lead.md
  lumina-sales-lead.md
```

## 使い方（概要）

1. Claude Codeの `Agent` ツールで `subagent_type: "lumina-ceo"` を呼び出し、やりたいことを相談する。
2. CEOが返す割り振り方針に従って、該当する部門リーダー（`lumina-eng-lead` / `lumina-design-lead` / `lumina-marketing-lead` / `lumina-sales-lead`）を呼び出す。
3. 各部門の成果物を再度 `lumina-ceo` に渡し、最終報告をまとめてもらう。

単一部門だけで完結する依頼は、CEOを経由せず該当部門に直接依頼してよい。

詳細は [processes/task-intake.md](processes/task-intake.md) を参照。

## 注意

Lumina Worksは実在の企業ではなく、架空のロールプレイ用設定です。生成される提案・コピー・見積りなどはすべてフィクションであり、実際の事業判断の根拠にはしないでください。
