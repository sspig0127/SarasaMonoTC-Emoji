# SarasaMonoTC-Emoji 改善路線圖

> 最後更新：2026-03-30（v1.5 完成；75 tests；CBLC debug log 強化）

---

## 版本規劃概覽

| 版本 | 重點 | 狀態 |
|------|------|------|
| **v1.0** | 初始版本：Color 變體（CBDT/CBLC） | ✅ 已發佈 |
| **v1.1** | 新增 Lite 變體（glyf 單色） | ✅ 已發佈 |
| **v1.2** | 修正 Lite emoji 尺寸（UPM 2048→1000 縮放） | ✅ 已發佈 |
| **v1.3** | 測試框架 + 健壯性改善 | ✅ 完成（T1–T4） |
| **v1.4** | COLRv1 第三變體（彩色向量） | ✅ 已發佈 |
| **v1.4.1** | COLRv1 greedy 選取（修復網頁亂碼） | ✅ 完成 |
| **v1.4.2** | COLRv1 priority allowlist（dev emoji 保證彩色） | ✅ 已發佈 |
| **v1.5** | BMP 符號彩色覆蓋（force_color / force_colrv1_codepoints）；post 3.0→2.0 升級；75 tests | ✅ 完成 |
| **v1.5.1** | force BMP 清單 5 → 15（↩⌨☀☁⚙❄❌➡⬆⬇）；Budget 8132→8091 slots | ✅ 完成 |
| **v2.0** | ZWJ 序列 / 旗幟 / 膚色變體 | 🔮 未來 |

---

## v2.0 — 完整 Emoji 支援（長期）

目前約 40% 現代 emoji 因需要 ZWJ 序列而缺席。v2.0 目標是補齊這個缺口。

### 缺席類型分析

| 類型 | 範例 | 數量 | 技術需求 |
|------|------|------|----------|
| 膚色變體 | 👋🏻（U+1F44B + U+1F3FB） | 125+ 個基底 | codepoint sequence → GSUB ligature |
| ZWJ 家庭 | 👨‍👩‍👧‍👦 | 100+ 個 | ZWJ（U+200D）序列 |
| 旗幟 | 🇺🇸（U+1F1FA + U+1F1F8） | 250+ 面 | Regional Indicator 雙字元 |
| 性別變體 | 🏃‍♀️ vs 🏃‍♂️ | 70+ 個 | ZWJ + U+2640/2642 |
| 職業 emoji | 👩‍💻 | 100+ 個 | ZWJ 序列 |

### 技術方向
- 解析 NotoColorEmoji 的 GSUB table（LookupType 4：Ligature Substitution）
- 建立 ZWJ sequence → glyph name 的對應表
- 將 sequence 加入 GSUB ligature rules，cmap 指向分解後的 input sequence
- 旗幟：Regional Indicator 需特殊處理（兩個字元組合）

### 參考資源
- [Unicode Emoji ZWJ Sequences](https://unicode.org/emoji/charts/emoji-zwj-sequences.html)
- [OpenType GSUB Ligature Substitution](https://learn.microsoft.com/en-us/typography/opentype/spec/gsub#42-lookup-type-4-ligature-substitution-subtable)
- [noto-emoji GSUB 實作](https://github.com/googlefonts/noto-emoji/blob/main/add_emoji_gsub.py)

---

## v1.5 — BMP 符號彩色覆蓋 ✅ 完成

**問題**：❤（U+2764）、⭐（U+2B50）、⚠（U+26A0）等 BMP 符號在所有變體中呈現黑白，
因 `skip_existing: true` 讓 Sarasa 的單色字形優先。

**解決方案**：config.yaml 白名單，各變體各自強制彩色覆蓋。

### COLRv1 變體（`colrv1.force_colrv1_codepoints`）

**技術實作**（三個修改位置）：

| 位置 | 修改內容 |
|------|----------|
| `merge_emoji_colrv1` Step 2.5 | 建立 `glyph_forced_rename`（如 `uni2764 → uni2764_colrv1`），僅限與 Sarasa 字形名稱衝突的強制 codepoint |
| `merge_emoji_colrv1` Step 3 | `skip_existing` 過濾時保留強制 codepoint |
| `_update_cmap` | 新增 `force_codepoints` 參數，對強制清單允許覆蓋 BMP cmap 已有項目（原有 `if cp not in cmap` guard） |

**Greedy 選取**：強制 codepoint 與 `priority_codepoints` 合併為 Phase 0/1，保證優先選入。
**Dep 收集**：dep lookup 使用原始名稱（`uni2764`）以查到 COLR 記錄，rename 在 greedy 結束後才套用。
**COLR 更新**：deep copy 後將 `BaseGlyphPaintRecord.BaseGlyph` 從 `uni2764` 改為 `uni2764_colrv1`。

### Color 變體（`emoji.force_color_codepoints`）

**技術實作**（三個修改位置）：

| 位置 | 修改內容 |
|------|----------|
| `merge_emoji` Step 3 | `skip_existing` 過濾時保留強制 codepoint |
| `merge_emoji` Step 3.5 | 建立 `color_forced_rename`（如 `uni2764 → uni2764_color`）；更新 `emoji_cmap` |
| `merge_emoji` Step 4.5 | CBLC deep copy 後將 IndexSubTable 內的原始名稱重新命名（在 `_filter_cblc_to_added_glyphs` 之前） |

**CBLC 順序限制**：`emoji_glyphs_to_add` 保持 NotoColorEmoji glyph order（嚴格遞增 ID 要求），
rename 後的字形在原始位置插入，不附加至末尾。

**post table 升級**：Sarasa 使用 post format 3.0（不儲存字形名稱）。`color_forced_rename` 啟用時，
`merge_emoji` Step 9.5 自動升級至 format 2.0，使 `uni2764_color` 等自訂後綴在 save/reload 後持久化。

**預設清單**（5 個，config.yaml）：❤ U+2764、⭐ U+2B50、⚠ U+26A0、☺ U+263A、⚡ U+26A1（兩變體相同）
⚠ 修改其中一個清單時，請同步修改另一個（`emoji.force_color_codepoints` ↔ `colrv1.force_colrv1_codepoints`）。

### 測試

75 tests（70 原有 + 3 新增 `TestUpdateCmapForceOverrideColor` + 2 新增 post format 升級驗證）

新增測試（`tests/test_font_output.py`）：
- `test_post_format_2_when_force_codepoints`：確認 force_color_codepoints 啟用時，post table 必須為 format 2.0
- `test_forced_bmp_codepoints_use_color_glyph`：確認 5 個強制 BMP codepoint 在 reload 後仍指向 `_color` 後綴字形

---

## v1.4.2 — COLRv1 Priority Allowlist（Dev Emoji 保證彩色）✅ 已發佈

**背景**：v1.4.1 greedy 選取以 codepoint 升序截止於 ~U+1F4FB，
導致高 codepoint dev emoji（🔧 🔗 🚀 🔒 等，U+1F500+）未被選入。

**修復**：兩階段選取 Phase 1 改為先保證 27 個高頻 dev/tooling emoji 入選，再以 greedy 填充其餘預算。

**Phase 1 — Priority 清單挑選依據**（3 項條件）：
1. 在 GitHub README / 技術文件中出現頻率高（🔧 ⚙️ 🚀 🔒 📦 等）
2. **不在 BMP**（U+0000–U+FFFF）：BMP 符號 Sarasa 原生已有，`skip_existing` 正確跳過；
   若需 BMP 符號顯示彩色，改用 `force_colrv1_codepoints`（v1.5 新增）
3. COLRv1 greedy 截止點之後（U+1F500+），greedy 無法自動選入

**Phase 2 — Greedy 填充**：剩餘預算以 codepoint 升序選入，首個超預算停止。

- Priority 27 個 emoji 共消耗 27 slots（每個邊際成本 = 1，零幾何依賴）
- 詳見 `config.yaml` `colrv1.priority_codepoints` 區塊的說明註解

**附帶更新**：
- `verify-emoji.html` 新增 Section 3：GitHub/程式文件常用符號驗證（8 個分類）
- `docs/colrv1-emoji-list.json` 新增 `priority` 欄位（bool）

---

## v1.4.1 — COLRv1 Greedy 選取（修復網頁亂碼）✅ 完成

**問題**：COLRv1 全量合併（~1,358 emoji + ~7,536 geometry deps = ~8,900+ new glyphs）
導致部分瀏覽器 / OTS 產生亂碼。

**修復**：`merge_emoji_colrv1()` 新增兩階段選取邏輯，在 `max_new_glyphs`（預設 8,136）預算內選取最多 emoji。

**Phase 1 — Priority 優先**：保證 GitHub/程式文件常用 dev emoji 必選（27 個，codepoint 升序），
不受截止點限制（🔧 U+1F527、🔗 U+1F517、🚀 U+1F680、🔒 U+1F512 等）。

**Phase 2 — Greedy 填充**：剩餘預算以 codepoint 升序選入常用舊 emoji，首個超預算則停止。

- 選取結果：600 個 emoji（27 priority + 573 greedy），glyph 成本 8,132/8,136 slots
- 選取清單存於 `docs/colrv1-emoji-list.json`（含 codepoint、unicode name、成本、priority 旗標）
- 可透過 `config.yaml` 的 `colrv1.max_new_glyphs` 調整預算
- 可透過 `config.yaml` 的 `colrv1.priority_codepoints` 自訂優先 emoji 清單
- 詳見 `PLAN-COLRv1-greedy.md`

---

## v1.4 — COLRv1 變體（彩色向量）✅ 已發佈

作為「彩色但輕量」的第三選項。使用 `--colrv1` 旗標建構，詳見 `PLAN-COLRv1.md`。

| 比較項目 | CBDT/CBLC（Color） | glyf（Lite） | COLRv1 |
|---------|-------------------|-------------|--------|
| 顏色 | ✅ 彩色 | ❌ 單色 | ✅ 彩色 |
| Emoji 數量 | 1,358 | 1,358 | 600（greedy 選取） |
| 檔案大小 | ~35 MB | ~25 MB | ~26 MB（實測） |
| VHS/Chromium | ⚠️ 不穩定 | ✅ 完全支援 | ✅ Chrome 98+ |
| 向量縮放 | ❌ 點陣圖 | ✅ 向量 | ✅ 向量 |

來源字體：`Noto-COLRv1.ttf`（`googlefonts/noto-emoji` repo 的 `fonts/` 目錄）

---

## v1.3 — 測試框架與健壯性 ✅ 完成

### 目標
建立可靠的測試基礎，防止後續開發引入回歸問題；補強邊界條件處理。

### 功能清單

#### T1 — 基本測試框架 ✅
- [x] 建立 `tests/` 目錄結構
- [x] `tests/test_font_output.py`：驗證建構結果
  - 所有 emoji glyph 寬度 = 2× half-width
  - 關鍵 codepoint 存在（😀 U+1F600、🔥 U+1F525、一 U+4E00）
  - Color 版有 CBDT/CBLC、無 glyf-only emoji；Lite 版反之
  - 建構前後 glyph 總數合理範圍（Sarasa 原始 + emoji 數量）
- [x] `tests/test_emoji_merge.py`：單元測試核心函式
  - `detect_font_widths()` 正確偵測已知字體
  - `get_emoji_cmap()` 過濾 ASCII / Variation Selector
  - `_scale_glyph()` 縮放後 bbox 為整數且在 int16 範圍內
- [x] CI/CD：GitHub Actions workflow，PR 觸發自動測試

#### T2 — UPM 縮放保護 ✅
- [x] `_scale_glyph()` 加 int16 範圍驗證（-32768 ~ 32767）
- [x] 若縮放後超界，raise `ValueError` 並說明原因
- [x] 在 `merge_emoji_lite()` 加縮放結果摘要 log（yMin/yMax 樣本）

#### T3 — verify-emoji.html 加 Lite / COLRv1 切換 ✅
- [x] 加入變體切換器（Color / Lite / COLRv1 下拉選單）
- [x] 各變體切換至對應 `output/fonts-*/` 路徑
- [x] 加入「emoji 視覺尺寸對比文字」測試 case

#### T4 — 建構健壯性 ✅
- [x] 平行建構失敗時清理 partial output
- [x] `detect_font_widths()` fallback 加最低佔比門檻（≥ 1% glyph）
- [x] 建構耗時紀錄（每個 style 幾秒，總計）

---

## 外部專案評估

### Sarasa-Mono-TC-Nerd（AlexisKerib/Sarasa-Mono-TC-Nerd）

> 評估日期：2026-03-29 | 評估目的：是否納入 Lite 變體或作為獨立第三變體

**專案概述：** 將 Sarasa Mono TC 與 Nerd Fonts 圖示整合的 TTF 字體，維持中英文 2:1 等寬比。

| 項目 | 內容 |
|------|------|
| 建立時間 | 2020-12（約 5 年未更新） |
| 提交數 | 30 commits |
| 狀態 | 🟡 維護停滯（dormant） |
| 新增內容 | Nerd Fonts PUA 圖示（排除 Material Design 以控制大小） |
| Emoji 支援 | ❌ 無 |
| 格式 | TTF 單色 glyf |
| VHS 相容性 | 未測試（但 glyf 格式理論上相容） |
| 建構方式 | Nerd Fonts 官方 patch 腳本 |
| 授權 | 開源（fork 自 XuanXiaoming/Sarasa-Mono-SC-Nerd） |

**結論與建議：**

1. **短期（v1.x）— 不納入**：Sarasa-Mono-TC-Nerd 已 5 年未更新，Nerd Fonts 版本落後；直接整合風險高、效益低。
2. **中期（v2.x）— 可評估「Nerd 變體」**：參考其方法，使用 Nerd Fonts 官方 fontpatcher 腳本，在本專案自行建構「SarasaMonoTCEmojiNerd」第三變體——同時含 emoji + Nerd Fonts 圖示。
3. **主要挑戰**：Nerd Fonts 使用 PUA（私用區 U+E000–U+F8FF 等）codepoint，與 emoji 不重疊，技術上可並行嵌入；但字體檔案大小將增加（估 +2～5 MB）。
4. **參考方法**：[Nerd Fonts fontpatcher](https://github.com/ryanoasis/nerd-fonts/blob/master/font-patcher) — 官方 Python 腳本，可在 fonttools 建構流程後作為後處理步驟調用。

---

## 已知技術債

| 項目 | 位置 | 說明 |
|------|------|------|
| CBLC filtering 可能移除有效 emoji | `emoji_merge.py:_filter_cblc_to_added_glyphs` | 名稱衝突時捨棄 color bitmap，以 Sarasa outline 代替。Build log 現會列出被移除的 glyph 名稱（最多 10 個），可評估是否需加入 `force_color_codepoints` |
| ~~BMP 符號（☺️ ⭐ ⚠️ 等）在 COLRv1 呈現黑白~~ | `emoji_merge.py` | ✅ 已修正（v1.5）：`force_colrv1_codepoints` 白名單；`_update_cmap` BMP guard 修正；`glyph_forced_rename`（`uni2764 → uni2764_colrv1`）機制 |
| ~~Mac platform name 移除時機~~ | `build.py` | ✅ 已修正（v1.3）：在 `update_font_names()` 之後再次呼叫 `_strip_mac_name_records` |
| ~~config 型別未驗證~~ | `build.py` | ✅ 已修正：新增 `get_config_int()` helper，`parallel` 與 `emoji_width_multiplier` 讀取時驗證型別與範圍 |
| ~~`emoji_width_multiplier` 無範圍檢查~~ | `src/config.py` | ✅ 已修正：`FontConfig.__post_init__` 驗證型別為 int 且範圍在 [1, 4] |
| ~~COLRv1 全量合併導致網頁亂碼~~ | `src/emoji_merge.py` | ✅ 已修正（v1.4.1）：greedy 選取限制新增 glyph ≤ 8,136 slots |
