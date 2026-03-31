# SarasaMonoTC-Emoji 路線圖

> 最後更新：2026-03-31（v2.0 sequence MVP 已串通三變體）
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
| v2.0 | ZWJ 序列 / 旗幟 / 膚色變體 | 🚧 進行中 |
| v2.x | 評估第四變體：Emoji + Nerd Fonts PUA | 🔍 評估中 |

---

## v2.0 — 完整 Emoji 支援（進行中）

目前約 40% 現代 emoji 因需要 ZWJ 序列而缺席。v2.0 目標是補齊這個缺口。

| 類型 | 範例 | 技術需求 |
|------|------|---------|
| 膚色變體 | 👋🏻 | codepoint sequence → GSUB ligature |
| ZWJ 家庭 | 👨‍👩‍👧‍👦 | ZWJ（U+200D）序列 |
| 旗幟 | 🇺🇸 | Regional Indicator 雙字元 |
| 性別 / 職業 | 👩‍💻 | ZWJ + U+2640/2642 |

**技術方向**：解析來源 emoji 字體的 GSUB（LookupType 4），建立 ZWJ sequence → glyph 對應，
再把 sequence 規則生成到 merged font。細部拆解見 [`docs/v2-sequence-implementation.md`](./docs/v2-sequence-implementation.md)。

### 目前進度

- 已完成：
  - `extract_emoji_sequences()` 與 shared `EmojiEntry` metadata
  - `Color` / `Lite` / `COLRv1` 三條 merge pipeline 的 sequence-aware 輸入
  - 三個變體的 GSUB sequence ligature 寫入
  - source / unit / output tests
  - `verify-emoji.html` 的 ZWJ / 膚色 / 旗幟驗證區
- 已驗證代表樣本：
  - `👩‍💻`
  - `👋🏻`
  - `🇺🇸`
- 目前 COLRv1 採保守策略：
  - 先做既有 single-codepoint greedy 選取
  - 再用剩餘 glyph budget 選入 sequence
  - `config.yaml` 的 `colrv1.priority_sequences` 可保證高價值 sequence 優先納入

### 目前仍未完成

- 全 style 自動化驗證仍以 `Regular` 為主
- COLRv1 sequence 仍不是全量納入，而是 budget 內的優先 / greedy 選取
- release notes / 版本號 / 發佈流程尚未切到 v2.0

### 實作拆解建議

| Phase | 目標 | 主要輸出 |
|------|------|---------|
| P1 | 先支援單一來源字體已有的 sequence emoji 映射 | sequence → glyph 對照表、基本測試 | ✅ |
| P2 | 將 sequence 產生為 Sarasa 端可用的 GSUB ligature | merged GSUB、cmap / glyph order 整合 | ✅ |
| P3 | 先補齊高價值序列 | ZWJ 家庭、性別職業、膚色變體、旗幟 | ✅ MVP |
| P4 | 補測試與驗證工具 | sequence regression tests、verify 頁增加 sequence 專區 | ✅ MVP |
| P5 | 擴到所有 style 與 release 流程 | 全 style 驗證、版本 / 發佈整理 | 🔜 |

### 程式面需要新增的能力

1. 解析來源字體 GSUB
   - 讀出 ligature substitution（LookupType 4）
   - 建立 `codepoint sequence -> source glyph name` 對照
2. sequence-aware glyph 收集
   - 目前 `get_emoji_cmap()` 只處理 `getBestCmap()` 的單一 codepoint
   - v2.0 需要新增 sequence extractor，不能只靠 cmap
3. merged font 的 GSUB 生成 / 合併
   - 為 sequence 輸入建立 ligature 規則
   - 讓 `👨 + ZWJ + 👩 + ZWJ + 👧 + ZWJ + 👦 -> family glyph`
4. 變體一致性處理
   - Color / Lite / COLRv1 都要能吃同一份 sequence metadata
   - glyph 輪廓、bitmap、paint tree 各自複製，但 sequence 規則應盡量共用管線

### 已完成的最小可行版本

- 已選一小組高價值 sequence：
  - `👩‍💻`
  - `👨‍💻`
  - `👩‍🔬`
  - `👨‍👩‍👧‍👦`
  - `👋🏻`
  - `🇺🇸`
- 已先在 `Regular` 跑通 end-to-end
- 已擴到三變體：
  - `Lite`
  - `Color`
  - `COLRv1`

### 下一步建議

- 補 `Italic / Bold / BoldItalic` 的 output font 自動化檢查
- 決定 COLRv1 sequence 是否需要擴增 `priority_sequences`
- 規劃版本號、release note、zip / manifest 更新策略

### 測試需求（目前狀態）

- 已完成：
  - pure logic：sequence parser、GSUB rule builder
  - source font：來源字體確實含對應 ligature / glyph
  - output font：代表 sequence 在 merge 後能映射到正確 glyph
  - visual：verify 頁已新增 ZWJ、膚色、旗幟三類樣本
- 尚待補強：
  - 非 `Regular` style 的 output assertions
  - 更多 sequence 覆蓋樣本與回歸範圍

---

## v2.x — 評估第四變體：Emoji + Nerd Fonts PUA

除了目前三個變體（Color / Lite / COLRv1），中期可評估新增一條「emoji + Nerd Fonts PUA」產品線，
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

建議順序：
1. 先完成 v2.0 sequence emoji
2. 再評估以 Nerd Fonts `font-patcher` 或等價流程，將 PUA glyph merge 進既有輸出字體
3. 優先從 `Lite` 或 `COLRv1` 變體試做，再決定是否擴到 `Color`

原因：
- v2.0 已經會引入新的 GSUB / sequence metadata 複雜度
- Nerd Fonts PUA 屬另一條 glyph merge 管線，若同時開工，問題來源會很難切分
- 先在較容易 debug 的變體試做，較容易看清 glyph order、name table、寬度與 PUA 對映問題

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
- 先挑一小組高頻 icon：
  - branch / git
  - folder / file
  - terminal / prompt
  - dev language / tooling icon
- 驗證項目：
  - PUA codepoint 是否正確映射
  - monospace 寬度是否穩定
  - 與 emoji 共存時是否出現 glyph order / name collision
  - 終端機、VS Code、瀏覽器 verify 頁是否都能正確顯示

### 暫時結論

- 這個方向有產品價值，適合列入 `v2.x` 評估項目
- 但不建議插隊到 `v2.0` 主線之前
- 建議等 sequence emoji 先穩定後，再以獨立分支或獨立實驗腳本驗證

參考：
- [Nerd Fonts font-patcher](https://github.com/ryanoasis/nerd-fonts/blob/master/font-patcher)

---

## 待解技術債

| 項目 | 位置 | 說明 |
|------|------|------|
| CBLC filtering 可能移除有效 emoji | `emoji_merge.py:_filter_cblc_to_added_glyphs` | 名稱衝突時捨棄 color bitmap。Build log 列出被移除的 glyph 名稱（最多 10 個），可評估是否需加入 `force_color_codepoints` |
| output tests 只檢查 Regular | `tests/conftest.py`、`tests/test_font_output.py` | Italic / Bold / BoldItalic 目前靠 build 成功與人工驗證，還沒有對 output font 做自動化檢查 |
| COLRv1 sequence 仍為 budget-limited | `config.yaml`、`emoji_merge.py:merge_emoji_colrv1` | COLRv1 已支援 sequence，但目前先用剩餘 glyph budget 選入，尚非全量 sequence 覆蓋 |
