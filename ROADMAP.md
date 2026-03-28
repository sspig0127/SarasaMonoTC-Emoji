# SarasaMonoTC-Emoji 改善路線圖

> 最後更新：2026-03-29

---

## 版本規劃概覽

| 版本 | 重點 | 狀態 |
|------|------|------|
| **v1.0** | 初始版本：Color 變體（CBDT/CBLC） | ✅ 已發佈 |
| **v1.1** | 新增 Lite 變體（glyf 單色） | ✅ 已發佈 |
| **v1.2** | 修正 Lite emoji 尺寸（UPM 2048→1000 縮放） | ✅ 已發佈 |
| **v1.3** | 測試框架 + 健壯性改善 | 🔨 進行中（T1 ✅） |
| **v2.0** | ZWJ 序列 / 旗幟 / 膚色變體支援 | 🔮 未來 |
| **v2.x** | COLRv1 第三變體（彩色向量） | 🔮 未來 |

---

## v1.3 — 測試框架與健壯性（近期）

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

#### T3 — verify-emoji.html 加 Lite 切換 ✅
- [x] 加入變體切換器（Color / Lite 下拉選單）
- [x] Lite 模式下切換至 `output/fonts-lite/` 路徑
- [x] 加入「emoji 視覺尺寸對比文字」測試 case

#### T4 — 建構健壯性
- [ ] 平行建構失敗時清理 partial output
- [ ] `detect_font_widths()` fallback 加最低佔比門檻（≥ 1% glyph）
- [ ] 建構耗時紀錄（每個 style 幾秒，總計）

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

## v2.x — COLRv1 變體（彩色向量）

作為「彩色但輕量」的第三選項。

| 比較項目 | CBDT/CBLC（Color） | glyf（Lite） | COLRv1 |
|---------|-------------------|-------------|--------|
| 顏色 | ✅ 彩色 | ❌ 單色 | ✅ 彩色 |
| 檔案大小 | ~35 MB | ~25 MB | ~15 MB（估） |
| VHS/Chromium | ⚠️ 不穩定 | ✅ 完全支援 | ✅ Chrome 98+ |
| 向量縮放 | ❌ 點陣圖 | ✅ 向量 | ✅ 向量 |

來源字體：`Noto-COLRv1.ttf`（已在 `googlefonts/noto-emoji` repo 的 `fonts/` 目錄）

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
| CBLC filtering 可能移除有效 emoji | `emoji_merge.py:181-237` | 名稱衝突時捨棄 color bitmap，以 Sarasa outline 代替 |
| ~~Mac platform name 移除時機~~ | `build.py` | ✅ 已修正（v1.3）：在 `update_font_names()` 之後再次呼叫 `_strip_mac_name_records` |
| config 型別未驗證 | `build.py:42-51` | `get_config_value()` 不驗證型別，錯誤訊息不友善 |
| `emoji_width_multiplier` 無範圍檢查 | `src/config.py` | 允許無效值（< 1 或 > 4） |
