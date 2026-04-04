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
| v2.x | 第四變體 Nerd Lite（Emoji + Nerd Fonts PUA） | 🚧 MVP 完成，待 merge |

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

## v2.x — 第四變體 Nerd Lite（Emoji + Nerd Fonts PUA）

以 Lite 為底，合併 Nerd Fonts BMP PUA icon，讓單一字體同時具備中文、emoji 與常用開發圖示。

字族名稱：`SarasaMonoTCEmojiLiteNerd`；建構指令：`uv run python build.py --nerd-lite`

### 已完成（feature/nerd-lite-mvp，134 tests 全過）

- `src/emoji_merge.py`：`_load_nerd_pua_glyphs()`、`_merge_nerd_fonts_pua()`、`merge_emoji_lite_nerd()`
- `build.py`：`--nerd-lite` flag、`get_config_int_ranges()`
- `config.yaml`：`nerd_lite` 區塊（family_name、nerd_font、icon_ranges、single_column_ranges）
- **折衷方案（PUA 欄寬設計）**：
  - Powerline（E0A0–E0D7）：1 欄（scale=500/2048），確保 prompt / statusline 對齊
  - Devicons / Codicons / Octicons / Seti-UI（其餘集合）：2 欄（scale=1000/2048），視覺比例與 emoji 一致
- `tests/test_font_output.py`：`TestNerdLiteOutput`（7 tests）
- `verify-emoji.html`：Section 12（12.0 折衷方案說明 + 12.1–12.8 各集合驗證）

### 待辦

- PR / merge 回 main
- Release workflow 加入 `--nerd-lite` 建構步驟
- 補 Italic / Bold / BoldItalic output 斷言（與其他變體共同技術債）

### 參考文件

- 架構評估 → [`docs/nerd-fonts-variant-eval.md`](./docs/nerd-fonts-variant-eval.md)
- 實作計畫 → [`docs/nerd-lite-impl-plan.md`](./docs/nerd-lite-impl-plan.md)

---

## 待解技術債

| 項目 | 位置 | 說明 |
|------|------|------|
| CBLC filtering 可能移除有效 emoji | `emoji_merge.py:_filter_cblc_to_added_glyphs` | 名稱衝突時捨棄 color bitmap。Build log 列出被移除的 glyph 名稱（最多 10 個），可評估是否需加入 `force_color_codepoints` |
| output tests 只檢查 Regular | `tests/conftest.py`、`tests/test_font_output.py` | Italic / Bold / BoldItalic 目前靠 build 成功與人工驗證，還沒有對 output font 做自動化檢查 |
| COLRv1 sequence 仍為 budget-limited | `config.yaml`、`emoji_merge.py:merge_emoji_colrv1` | COLRv1 已支援 sequence，但目前先用剩餘 glyph budget 選入，尚非全量 sequence 覆蓋 |
