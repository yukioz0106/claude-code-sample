# ai_department — AI社員だけの課（ENEOS社内組織計画）

ENEOS社内に、AI社員だけで構成される課を新設し、他部署からの依頼に対応できる組織・機能を構築するための計画書と、その体制を実装するClaude Codeカスタムサブエージェント群の定義である。

架空企業のロールプレイ用である `ai_company`（Lumina Works）とは異なり、本ディレクトリはENEOS社内の実組織を想定した計画である。実運用には情報システム部門・情報セキュリティ部門・コンプライアンス部門の正式な承認が必要であり、現時点では計画・設計段階にある。

## 構成

```　　
ai_department/
  PLAN.md                           計画書本体（目的・業務範囲・体制・フロー・セキュリティ・導入ステップ）
  org-chart.md                      組織図、エージェント対応表、意思決定フロー
  roles/
    section-lead.md                 課長の役割定義
    docs-specialist.md              資料作成・文書化担当の役割定義
    data-specialist.md              データ分析・集計担当の役割定義
    it-support-specialist.md        IT・システム軽微開発支援担当の役割定義
    helpdesk-specialist.md          問い合わせ対応・一次窓口担当の役割定義
  processes/
    task-intake.md                  依頼の受付フロー
    security-and-governance.md      セキュリティ・機密情報の取り扱い
    human-review.md                 人間による承認・レビュー体制
    rollout-plan.md                 導入ステップ・費用対効果

.claude/agents/
  ai-dept-lead.md
  ai-dept-docs.md
  ai-dept-data.md
  ai-dept-itsupport.md
  ai-dept-helpdesk.md
```

## 使い方（概要）

1. まず [PLAN.md](PLAN.md) を読み、目的・業務範囲・セキュリティ方針・導入ステップを把握する。
2. Claude Codeの `Agent` ツールで `subagent_type: "ai-dept-lead"` を呼び出し、依頼内容を相談する。
3. 課長が返す振り分け方針に従って、該当する専門AI社員（`ai-dept-docs` / `ai-dept-data` / `ai-dept-itsupport` / `ai-dept-helpdesk`）を呼び出す。
4. 成果物は必ず人間がレビューしたうえで依頼元部署に納品する（[processes/human-review.md](processes/human-review.md)）。

単一分野で完結する軽微な依頼は、課長を経由せず該当する専門AI社員に直接依頼してよい。詳細は [processes/task-intake.md](processes/task-intake.md) を参照。

## 重要な注意

- 機密情報・個人情報・取引上重要な情報は、現状の仕組みに入力しないことを原則とする（[processes/security-and-governance.md](processes/security-and-governance.md)）。
- AI社員の成果物は、ノーレビューで依頼元・意思決定に直結させない。
- 本計画は実運用の承認を得たものではなく、協議のための出発点である。
