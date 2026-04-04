# SarasaMonoTC-Emoji 路線圖

> 最後更新：2026-04-04（精簡 v2.0 規劃細節；歷史內容移至 roadmap-history.md）
>
> **歷史版本實作細節** → [`docs/roadmap-history.md`](./docs/roadmap-history.md)（需要查閱時再 Read）
> **COLRv1 深度技術細節** → [`.github/colrv1-dev-notes.md`](./.github/colrv1-dev-notes.md)
> **v2.0 實作設計** → [`docs/v2-sequence-implementation.md`](./docs/v2-sequence-implementation.md)

---

## 版本規劃概覽

| 版本 | 重點 | 狀態 |
|------|------|------|
| v1.0–v1.3 | Color / Lite 變體、測試框架 | ✅ 已發佈 |
| v1.4 | COLRv1 第三變體（彩色向量） | ✅ 已發佈 |
| v1.4.1 | COLRv1 greedy 選取（修復網頁亂碼） | ✅ 完成 |
| v1.4.2 | COLRv1 priority allowlist（dev emoji 保證彩色） | ✅ 已發佈 |
| v1.5 | BMP 符號彩色覆蓋；post 3.0→2.0 升級；75 tests | ✅ 完成 |
| v1.5.1 | force BMP 清單 5→15；Budget 8132→8091 slots | ✅ 完成 |
| **v1.5.2** | COLRv1 paint 座標 + helper metrics 修復（🟡🟢 Chromium 渲染回歸） | ✅ 完成 |
| **v1.5.3** | COLRv1 高風險樣本驗證頁 + 全域 transformed-helper regression test | ✅ 完成 |
| v2.0 | ZWJ 序列 / 旗幟 / 膚色變體 + release workflow 收尾 | ✅ 已發佈 |
| v2.x | 評估第四變體：Emoji + Nerd Fonts PUA | 🔍 評估中 |

---

## v2.0 — 完整 Emoji 支援（已發佈 / 維護中）

v2.0.0 已補齊 sequence emoji 缺口；此段保留作為設計與維護背景。

| 類型 | 範例 | 技術需求 |
|------|------|---------|
| 膚色變體 | 👋🏻 | codepoint sequence → GSUB ligature |
| ZWJ 家庭 | 👨‍👩‍👧‍👦 | ZWJ（U+200D）序列 |
| 旗幟 | 🇺🇸 | Regional Indicator 雙字元 |
| 性別 / 職業 | 👩‍💻 | ZWJ + U+2640/2642 |

**技術方向**：解析來源 emoji 字體的 GSUB（LookupType 4），建立 ZWJ sequence → glyph 對應，
再把 sequence 規則生成到 merged font。細部設計見 [`docs/v2-sequence-implementation.md`](./docs/v2-sequence-implementation.md)。

### 已完成

- Color / Lite / COLRv1 三條 merge pipeline 全串通 sequence emoji
- Lite：所有 RI-pair 旗幟全域套用 2-column 自訂旗面（53 helper glyph，無白名單）
- Release workflow：`actions/checkout@v5` / `actions/cache@v5`
- 代表樣本已驗證：`👩‍💻` / `👋🏻` / `🇺🇸`

### 後續仍待補強（已歸入技術債）

- 非 `Regular` style 的 output font 自動化斷言（Italic / Bold / BoldItalic）
- COLRv1 sequence 仍為 budget-limited（priority + greedy，非全量）
- Release workflow 最後一個 Node.js 20 warning：`astral-sh/setup-uv@v4`（等上游 node24 版）

### 下一步

- 追蹤 `astral-sh/setup-uv` node24 版，屆時更新 release workflow
- 視需要調整 `colrv1.priority_sequences`
- 補非 Regular style 的 regression cases

> 規劃細節（實作拆解 / 各階段 MVP / 測試快照）→ [`docs/roadmap-history.md`](./docs/roadmap-history.md)

---

## v2.x — 評估第四變體：Emoji + Nerd Fonts PUA

v2.0 已發佈，前置條件達成，可開始評估。

除了目前三個變體（Color / Lite / COLRv1），中期可評估新增「emoji + Nerd Fonts PUA」產品線，
暫名可為 `SarasaMonoTCEmojiNerd`。

### 需求定位

目標使用者：
- 終端機 / shell prompt / editor 需要 Nerd Fonts icon 的使用者
- 同時希望保留本專案既有 emoji merge 能力的使用者

目標效果：
- 保留 Sarasa Mono TC 的中文字寬與可讀性
- 同時具備 emoji 與 Nerd Fonts PUA icon
- 減少使用者自行 patch 字體的額外步驟

### 可能技術路線

1. 以 Nerd Fonts `font-patcher` 或等價流程，將 PUA glyph merge 進既有輸出字體
2. 優先從 `Lite` 或 `COLRv1` 變體試做，再決定是否擴到 `Color`

原因：Nerd Fonts PUA 屬另一條 glyph merge 管線；先在較易 debug 的變體試做，問題來源較易切分。

### 主要風險

| 風險 | 說明 |
|------|------|
| 檔案大小再增加 | 已有 emoji merge 後，若再加入 Nerd Fonts PUA，四個 style 的發布包體積會再上升 |
| PUA 碼位衝突 | 需確認 Nerd Fonts 使用的 PUA 區段不會與現有字體或未來策略衝突 |
| 字寬一致性 | Nerd icon 不一定天然符合 2 columns / monospace 預期，需要額外調整 hmtx |
| glyph name / order 複雜化 | 目前已處理 emoji rename、COLRv1 helper glyph；再疊一層 PUA merge 會提高維護成本 |
| 授權與上游同步 | 需確認 Nerd Fonts patch 流程、來源版本與後續升級策略 |

### 建議驗證方式

- 先做單一 style MVP：`Regular`
- 先挑一小組高頻 icon：branch/git、folder/file、terminal/prompt、dev language
- 驗證項目：PUA mapping、monospace 寬度、glyph collision、終端機 / VS Code / verify 頁顯示

### 現況

- 有產品價值，列入 `v2.x` 評估項目
- 建議以獨立分支或獨立實驗腳本驗證，不影響主線穩定性
- 詳細評估（架構選項、PUA 分區分析、MVP 路線）→ [`docs/nerd-fonts-variant-eval.md`](./docs/nerd-fonts-variant-eval.md)

參考：[Nerd Fonts font-patcher](https://github.com/ryanoasis/nerd-fonts/blob/master/font-patcher)

---

## 待解技術債

| 項目 | 位置 | 說明 |
|------|------|------|
| CBLC filtering 可能移除有效 emoji | `emoji_merge.py:_filter_cblc_to_added_glyphs` | 名稱衝突時捨棄 color bitmap。Build log 列出被移除的 glyph 名稱（最多 10 個），可評估是否需加入 `force_color_codepoints` |
| output tests 只檢查 Regular | `tests/conftest.py`、`tests/test_font_output.py` | Italic / Bold / BoldItalic 目前靠 build 成功與人工驗證，還沒有對 output font 做自動化檢查 |
| COLRv1 sequence 仍為 budget-limited | `config.yaml`、`emoji_merge.py:merge_emoji_colrv1` | COLRv1 已支援 sequence，但目前先用剩餘 glyph budget 選入，尚非全量 sequence 覆蓋 |
