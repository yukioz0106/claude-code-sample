# 組織図

```
                 ┌───────────────┐
                 │      CEO       │
                 │ lumina-ceo     │
                 └───────┬────────┘
     ┌───────────┬────────┴────────┬───────────────┐
     │           │                 │                │
┌────▼────┐ ┌────▼─────┐   ┌───────▼───────┐ ┌──────▼───────┐
│Engineering│ │  Design  │   │  Marketing    │ │ Sales/BizDev  │
│eng-lead   │ │design-lead│  │marketing-lead │ │ sales-lead    │
└───────────┘ └──────────┘   └───────────────┘ └───────────────┘
```

## エージェント対応表

| 役職 | サブエージェント名 | 定義ファイル |
|---|---|---|
| CEO | `lumina-ceo` | `.claude/agents/lumina-ceo.md` |
| Engineeringリーダー | `lumina-eng-lead` | `.claude/agents/lumina-eng-lead.md` |
| Designリーダー | `lumina-design-lead` | `.claude/agents/lumina-design-lead.md` |
| Marketingリーダー | `lumina-marketing-lead` | `.claude/agents/lumina-marketing-lead.md` |
| Sales/BizDevリーダー | `lumina-sales-lead` | `.claude/agents/lumina-sales-lead.md` |

## 意思決定フロー

1. 依頼はまず CEO（`lumina-ceo`）が受ける。
2. CEOは依頼を分解し、関係する部門リーダーを1名以上指名する「割り振り方針」を提示する。
3. 指名された部門リーダーを個別に呼び出し、それぞれの成果物を作成する。
4. 各部門の成果物をCEOに戻し、全体の整合性を確認・統合した最終報告を作る。

CEO・部門リーダーは互いを直接呼び出さず、常に人間（またはClaude Codeの実行セッション）がハブとなって各エージェントを呼び出す構成にしている。これはエージェントの再帰呼び出しを避け、各ステップで判断内容を確認できるようにするため。
