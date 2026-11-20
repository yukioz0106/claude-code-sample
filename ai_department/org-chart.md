# 組織図・エージェント対応表

## 組織図

```
                 ┌─────────────────────┐
                 │   課長（セクションリード）  │
                 │   ai-dept-lead         │
                 └──────────┬──────────┘
      ┌───────────┬─────────┴─────────┬───────────────┐
      │           │                   │                │
┌─────▼─────┐┌────▼─────┐   ┌─────────▼────────┐ ┌──────▼───────┐
│資料作成・文書化│ │データ分析│   │IT・システム支援     │ │問い合わせ一次窓口│
│ai-dept-docs  │ │ai-dept-data│  │ai-dept-itsupport │ │ai-dept-helpdesk│
└──────────────┘ └──────────┘   └──────────────────┘ └───────────────┘
```

人間の管理者（オペレーター）が各AI社員を呼び出すハブとなる。AI社員同士は直接・再帰的に呼び出し合わない。

## エージェント対応表

| 役職 | サブエージェント名 | 定義ファイル | 役割詳細 |
|---|---|---|---|
| 課長（セクションリード） | `ai-dept-lead` | `.claude/agents/ai-dept-lead.md` | [roles/section-lead.md](roles/section-lead.md) |
| 資料作成・文書化担当 | `ai-dept-docs` | `.claude/agents/ai-dept-docs.md` | [roles/docs-specialist.md](roles/docs-specialist.md) |
| データ分析・集計担当 | `ai-dept-data` | `.claude/agents/ai-dept-data.md` | [roles/data-specialist.md](roles/data-specialist.md) |
| IT・システム軽微支援担当 | `ai-dept-itsupport` | `.claude/agents/ai-dept-itsupport.md` | [roles/it-support-specialist.md](roles/it-support-specialist.md) |
| 問い合わせ一次窓口担当 | `ai-dept-helpdesk` | `.claude/agents/ai-dept-helpdesk.md` | [roles/helpdesk-specialist.md](roles/helpdesk-specialist.md) |

## 意思決定フロー

1. 依頼はまず課長（`ai-dept-lead`）が受ける。
2. 課長は依頼を分解し、(a) 対応分野、(b) 機密情報の有無・対象外業務への該当可否、(c) 担当させるAI社員、を判断して「振り分け方針」を返す。機密情報の疑いがある場合、またはいずれの分野にも該当しない場合は、ただちに人間へのエスカレーションを提案する。
3. 振り分け方針に従い、該当するAI社員（1名以上）を個別に呼び出し、成果物のドラフトを作成する。複数分野にまたがる依頼で依存関係がなければ並列に呼び出してよい。
4. 各AI社員の成果物を人間のレビュー担当（必要に応じて課長にも）渡し、整合性・妥当性を確認する。
5. レビュー済みの成果物を依頼元部署に納品する。

## 設計上の注意

- 課長・各AI社員は、`ai_department/PLAN.md` と本ファイルを組織の前提として参照する。各役割の責務詳細は `ai_department/roles/` 配下、業務フロー・ガバナンスは `ai_department/processes/` 配下を参照。
- 既存の `ai_company`（架空企業Lumina Worksのシミュレーション）とは独立した、ENEOS社内の実組織を想定した計画である。名称・ツール権限を混同しないよう、サブエージェント名には `ai-dept-` プレフィックスを用いている。
