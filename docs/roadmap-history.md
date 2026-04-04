# SarasaMonoTC-Emoji 歷史版本實作細節

> 從 `ROADMAP.md` 分離（2026-03-30；v2.0 規劃細節於 2026-04-04 追加；v2.1 於 2026-04-04 追加）。
> 僅在需要查閱特定版本技術決策時才 Read 此檔案。
> 版本概覽與未來規劃 → [`ROADMAP.md`](../ROADMAP.md)
> COLRv1 深度技術細節 → [`.github/colrv1-dev-notes.md`](../.github/colrv1-dev-notes.md)

---

## v2.1 — Nerd Lite 第四變體實作細節存檔 ✅

> 歸檔自 ROADMAP.md（2026-04-04）。v2.1.0 已發佈。
> 架構評估 → [`docs/nerd-fonts-variant-eval.md`](./nerd-fonts-variant-eval.md)
> 實作計畫 → [`docs/nerd-lite-impl-plan.md`](./nerd-lite-impl-plan.md)

### 技術設計

- **來源字體**：`SymbolsNerdFontMono-Regular.ttf`（Nerd Fonts 3.4.0，UPM=2048）
- **PUA 集合**：Powerline（E0A0–E0D7）、Seti-UI（E5FA–E6FF）、Devicons（E700–E7FF）、Codicons（EA60–EBEB）、Octicons（F400–F4FF）
- **折衷方案欄寬**：
  - Powerline：1 欄（advance=500，scale=500/2048 ≈ 0.244）— prompt / statusline 精確對齊
  - 其餘集合：2 欄（advance=1000，scale=1000/2048 ≈ 0.488）— 視覺比例與 emoji 一致
- **`single_column_ranges`**：config.yaml 控制，可擴充

### 實作摘要（已全部完成）

| 檔案 | 新增內容 |
|------|---------|
| `src/emoji_merge.py` | `_load_nerd_pua_glyphs()`、`_merge_nerd_fonts_pua()`、`merge_emoji_lite_nerd()`（two-pass） |
| `build.py` | `--nerd-lite` flag、`get_config_int_ranges()`、`single_column_ranges` 參數 |
| `config.yaml` | `nerd_lite:` 區塊（family_name、nerd_font、icon_ranges、single_column_ranges） |
| `tests/conftest.py` | `nerd_font`、`output_nerd_lite_regular` fixtures |
| `tests/test_font_output.py` | `TestNerdLiteOutput`（7 tests；134 total） |
| `verify-emoji.html` | Section 12（12.0 折衷說明 + 12.1–12.8 各集合；字重切換修正） |
| `.github/workflows/release.yml` | `nerd_fonts_version` 參數、Nerd Fonts 下載、建構、打包、上傳 |

---

## v2.0 — 規劃與實作細節存檔 ✅

> 歸檔自 ROADMAP.md（2026-04-04）。v2.0 已發佈，以下為規劃期記錄。
> 實作設計全覽 → [`docs/v2-sequence-implementation.md`](../docs/v2-sequence-implementation.md)

### 實作拆解（已全部完成）

| Phase | 目標 | 主要輸出 | 狀態 |
|------|------|---------|------|
| P1 | 支援單一來源字體的 sequence emoji 映射 | sequence → glyph 對照表、基本測試 | ✅ |
| P2 | 將 sequence 產生為 Sarasa 端可用的 GSUB ligature | merged GSUB、cmap / glyph order 整合 | ✅ |
| P3 | 補齊高價值序列 | ZWJ 家庭、性別職業、膚色變體、旗幟 | ✅ |
| P4 | 補測試與驗證工具 | sequence regression tests、verify 頁 sequence 專區 | ✅ |
| P5 | 擴到所有 style 與 release 流程 | 全 style 驗證、版本 / 發佈整理 | ✅ |

### 程式面新增能力（已實作）

1. **GSUB 解析**：讀出 LookupType 4 ligature，建立 `codepoint sequence → source glyph name` 對照
2. **sequence-aware glyph 收集**：`extract_emoji_sequences()` 補充 `get_emoji_cmap()` 的 single-codepoint 限制
3. **merged font GSUB ligature 生成**：`👨 + ZWJ + 👩 + ZWJ + 👧 + ZWJ + 👦 → family glyph`
4. **三變體共用 sequence metadata**：Color / Lite / COLRv1 各自複製 glyph，但 sequence 規則共用管線

### MVP 初始驗證集（已擴增至全量 RI-pair）

當時先選六個樣本跑通 end-to-end，再擴到三變體：
`👩‍💻` `👨‍💻` `👩‍🔬` `👨‍👩‍👧‍👦` `👋🏻` `🇺🇸`

Lite 旗幟後來改為全域套用，不再限於 MVP 清單。

### 測試快照（v2.0 發佈時）

已完成：
- pure logic：sequence parser、GSUB rule builder
- source font：來源字體確實含對應 ligature / glyph
- output font：代表 sequence 在 merge 後能映射到正確 glyph
- visual：verify 頁已新增 ZWJ、膚色、旗幟三類樣本

仍待補強（已歸入技術債）：
- 非 `Regular` style 的 output assertions
- 更多 sequence 覆蓋樣本與回歸範圍

---

## v1.5.1 — force BMP 清單擴增 ✅

- `force_color_codepoints` / `force_colrv1_codepoints` 從 5 擴增至 15：
  新增 ↩⌨☀☁⚙❄❌➡⬆⬇（U+21A9 U+2328 U+2600 U+2601 U+2699 U+2744 U+274C U+27A1 U+2B06 U+2B07）
- 幾何 dep 共享節省：Budget 8132 → 8091 slots

---

## v1.5.2 — COLRv1 Chromium 渲染修復 ✅

**問題**：🟡 / 🟢 等高倍率 transform emoji 在 Chromium 中只剩 tiny fragment。

**修復**：
- `_scale_colrv1_paint_coords()` 將 COLR paint tree 的 font-unit 座標同步做 UPM 縮放
- `merge_emoji_colrv1()` 保留 geometry helper glyph 的縮放後 metrics，避免 helper glyph 被誤設為 `(0, 0)`

---

## v1.5.3 — 驗證與回歸覆蓋補強 ✅

- `verify-emoji.html` 新增來源字體對照與 COLRv1 高風險樣本區
- `tests/test_font_output.py` 新增：
  - `test_transformed_helper_glyph_metrics_preserved`
  - `test_all_transformed_helper_glyph_metrics_preserved`

---

## v1.5 — BMP 符號彩色覆蓋 ✅

**問題**：❤ ⭐ ⚠ 等 BMP 符號呈現黑白（`skip_existing: true` 讓 Sarasa 單色字形優先）。
**解決**：config.yaml 白名單，各變體各自強制彩色覆蓋。

### COLRv1 變體（`colrv1.force_colrv1_codepoints`）

| 位置 | 修改內容 |
|------|----------|
| `merge_emoji_colrv1` Step 2.5 | 建立 `glyph_forced_rename`（`uni2764 → uni2764_colrv1`） |
| `merge_emoji_colrv1` Step 3 | `skip_existing` 過濾時保留強制 codepoint |
| `_update_cmap` | 新增 `force_codepoints` 參數，允許覆蓋 BMP cmap 已有項目 |

### Color 變體（`emoji.force_color_codepoints`）

| 位置 | 修改內容 |
|------|----------|
| `merge_emoji` Step 3 | `skip_existing` 過濾時保留強制 codepoint |
| `merge_emoji` Step 3.5 | 建立 `color_forced_rename`（`uni2764 → uni2764_color`） |
| `merge_emoji` Step 4.5 | CBLC deep copy 後重新命名 IndexSubTable 內的原始名稱 |

**post table 升級**：`color_forced_rename` 啟用時，Step 9.5 自動升級 post format 3.0 → 2.0，
使 `uni2764_color` 等自訂後綴在 save/reload 後持久化。

**測試**：當時 75 tests（含 `test_post_format_2_when_force_codepoints`、`test_forced_bmp_codepoints_use_color_glyph`）

---

## v1.4.2 — COLRv1 Priority Allowlist ✅

**背景**：v1.4.1 greedy 截止於 ~U+1F4FB，導致高 codepoint dev emoji（🔧🔗🚀🔒 等）未被選入。
**修復**：兩階段選取，Phase 1 先保證 27 個高頻 dev emoji 入選，再 greedy 填充其餘預算。

Phase 1 挑選條件（3 項）：
1. GitHub README / CI 表格高頻出現
2. 不在 BMP（BMP 符號改用 `force_colrv1_codepoints`）
3. 位於 greedy 截止點之後（~U+1F500+）

---

## v1.4.1 — COLRv1 Greedy 選取（修復網頁亂碼）✅

**問題**：全量合併 ~8,900+ new glyphs 導致 OTS / 瀏覽器亂碼。
**修復**：greedy 兩階段選取，`max_new_glyphs`（預設 8,136）預算內選取最多 emoji。
- 當時選取結果：600 個 emoji（27 priority + 573 greedy），8,132/8,136 slots
- 選取清單：`docs/colrv1-emoji-list.json`

---

## v1.4 — COLRv1 變體 ✅

| 比較項目 | CBDT/CBLC（Color） | glyf（Lite） | COLRv1 |
|---------|-------------------|-------------|--------|
| 顏色 | ✅ | ❌ 單色 | ✅ |
| Emoji 數量 | 1,358 | 1,358 | 600（greedy） |
| 檔案大小 | ~35 MB | ~25 MB | ~26 MB |
| VHS/Chromium | ⚠️ | ✅ | ✅ Chrome 98+ |

來源字體：`Noto-COLRv1.ttf`（`googlefonts/noto-emoji`）

---

## v1.3 — 測試框架與健壯性 ✅

- T1：`tests/` 目錄、`test_font_output.py`、`test_emoji_merge.py`、GitHub Actions CI
- T2：`_scale_glyph()` int16 範圍驗證（-32768 ~ 32767）
- T3：`verify-emoji.html` 加變體切換器（Color / Lite / COLRv1）
- T4：平行建構失敗清理、`detect_font_widths()` fallback 門檻、建構耗時紀錄

---

## 外部專案評估：Sarasa-Mono-TC-Nerd

> 評估日期：2026-03-29

**結論**：5 年未更新，短期不納入。中期（v2.x）可自行建構「SarasaMonoTCEmojiNerd」（emoji + Nerd Fonts PUA）。
參考：[Nerd Fonts fontpatcher](https://github.com/ryanoasis/nerd-fonts/blob/master/font-patcher)

---

## 已解決技術債

| 項目 | 修正版本 |
|------|---------|
| Release workflow Node.js 20 warning（checkout/cache 已升 v5；setup-uv 仍待 node24） | 2026-04 |
| BMP 符號（☺ ⭐ ⚠ 等）在 COLRv1 呈現黑白 | v1.5 |
| Mac platform name 移除時機 | v1.3 |
| config 型別未驗證（parallel、emoji_width_multiplier） | v1.3 |
| COLRv1 全量合併導致網頁亂碼 | v1.4.1 |
| COLRv1 PaintColrLayers LayerList 未 walk（92% emoji 亂碼） | v1.4.1 |
| COLRv1 UPM 縮放未套用至 COLR paint coords（🟡🟢 9×9px） | v1.5.2 |
| COLRv1 helper glyph metrics 被清成 `(0, 0)`（Chromium transform fragment） | v1.5.2 |
