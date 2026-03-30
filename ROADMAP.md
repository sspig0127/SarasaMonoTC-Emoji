# SarasaMonoTC-Emoji 路線圖

> 最後更新：2026-03-31（文件同步更新；v2.0 實作設計補齊）
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
| v2.0 | ZWJ 序列 / 旗幟 / 膚色變體 | 🔮 未來 |

---

## v2.0 — 完整 Emoji 支援（長期）

目前約 40% 現代 emoji 因需要 ZWJ 序列而缺席。v2.0 目標是補齊這個缺口。

| 類型 | 範例 | 技術需求 |
|------|------|---------|
| 膚色變體 | 👋🏻 | codepoint sequence → GSUB ligature |
| ZWJ 家庭 | 👨‍👩‍👧‍👦 | ZWJ（U+200D）序列 |
| 旗幟 | 🇺🇸 | Regional Indicator 雙字元 |
| 性別 / 職業 | 👩‍💻 | ZWJ + U+2640/2642 |

**技術方向**：解析來源 emoji 字體的 GSUB（LookupType 4），建立 ZWJ sequence → glyph 對應，
再把 sequence 規則生成到 merged font。細部拆解見 [`docs/v2-sequence-implementation.md`](./docs/v2-sequence-implementation.md)。

### 實作拆解建議

| Phase | 目標 | 主要輸出 |
|------|------|---------|
| P1 | 先支援單一來源字體已有的 sequence emoji 映射 | sequence → glyph 對照表、基本測試 |
| P2 | 將 sequence 產生為 Sarasa 端可用的 GSUB ligature | merged GSUB、cmap / glyph order 整合 |
| P3 | 先補齊高價值序列 | ZWJ 家庭、性別職業、膚色變體、旗幟 |
| P4 | 補測試與驗證工具 | sequence regression tests、verify 頁增加 sequence 專區 |

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

### 建議先做的最小可行版本

- 先選一小組高價值 sequence：
  - `👩‍💻`
  - `👨‍💻`
  - `👩‍🔬`
  - `👨‍👩‍👧‍👦`
  - `👋🏻`
  - `🇺🇸`
- 先只在 `Regular` 跑通 end-to-end
- 確認資料模型穩定後，再擴到全部 style / 變體

### 測試需求（v2.0 前應先規劃）

- pure logic：sequence parser、GSUB rule builder
- source font：來源字體確實含對應 ligature / glyph
- output font：sequence 在 merge 後能映射到正確 glyph
- visual：verify 頁增加 sequence 區塊，至少含 ZWJ、膚色、旗幟三類樣本

---

## 待解技術債

| 項目 | 位置 | 說明 |
|------|------|------|
| CBLC filtering 可能移除有效 emoji | `emoji_merge.py:_filter_cblc_to_added_glyphs` | 名稱衝突時捨棄 color bitmap。Build log 列出被移除的 glyph 名稱（最多 10 個），可評估是否需加入 `force_color_codepoints` |
| 只支援單一 codepoint emoji | `emoji_merge.py:get_emoji_cmap` | 目前整條 merge pipeline 以 `getBestCmap()` 為入口，天然排除 ZWJ / 膚色 / 旗幟等 sequence emoji；這是 v2.0 的主要能力缺口 |
| output tests 只檢查 Regular | `tests/conftest.py`、`tests/test_font_output.py` | Italic / Bold / BoldItalic 目前靠 build 成功與人工驗證，還沒有對 output font 做自動化檢查 |
| sequence 視覺驗證缺口 | `verify-emoji.html` | 目前有單碼與 COLRv1 高風險樣本，但還沒有 ZWJ / 膚色 / 旗幟專區 |
