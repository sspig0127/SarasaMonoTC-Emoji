# Nerd Lite MVP — 實作計畫

> 建立：2026-04-04
> **✅ 已完成：feature/nerd-lite-mvp 已 merge，v2.1.0 發佈（2026-04-04）**
> 分支：`feature/nerd-lite-mvp`（已 merge 至 main）
> 評估背景：`docs/nerd-fonts-variant-eval.md`

## 目標

以 **Lite 變體為基礎**，新增「SarasaMonoTCEmojiLiteNerd」第四變體：
合併 Nerd Fonts PUA icon（glyf outline）進 Sarasa Mono TC，
讓一個字體檔同時擁有中文、emoji 與 Nerd Fonts icon。

MVP 範圍：Regular style only；BMP PUA 子集（開發者核心）。

---

## 來源字體

| 項目 | 值 |
|------|---|
| 路徑 | `fonts/NerdFontsSymbolsOnly/SymbolsNerdFontMono-Regular.ttf` |
| UPM | 2048 |
| BMP PUA glyph 數 | 3,500 |
| 授權 | MIT（Nerd Fonts）；各子集來源授權參見 Nerd Fonts repo |

### MVP icon 子集（BMP PUA）

| 集合 | 碼位區間 | glyph 數 | 說明 |
|------|---------|---------|------|
| Powerline Symbols | E0A0–E0D7 | 40 | prompt 分隔符、branch |
| Devicons | E700–E7FF | 256 | 語言 logo（Python、JS、Go、Rust） |
| Codicons | EA60–EBEB | 388 | VS Code 圖示集 |
| Octicons | F400–F4FF | 256 | GitHub（PR、issue、branch） |
| Seti-UI + Custom | E5FA–E6FF | 191 | 編輯器檔案類型 |

---

## 分工說明

### Copilot 負責（機械性、結構明確的任務）

標記為 `[Copilot]`：修改設定、boilerplate、文件更新、基本 smoke test。

### Claude Code 負責（架構設計、複雜邏輯、除錯）

標記為 `[Claude]`：核心 merge 函式、glyph 縮放整合、table 更新細節、回歸測試。

---

## Phase 0：環境準備

```bash
git checkout -b feature/nerd-lite-mvp
```

確認來源字體存在：
```bash
ls fonts/NerdFontsSymbolsOnly/SymbolsNerdFontMono-Regular.ttf
```

---

## Phase 1：config.yaml 擴充 `[Copilot]`

在 `colrv1:` 區塊之後，新增 `nerd_lite:` 區塊：

```yaml
# Nerd Lite variant — Lite + Nerd Fonts PUA icons
# Source: fonts/NerdFontsSymbolsOnly/SymbolsNerdFontMono-Regular.ttf (MIT)
# UPM: 2048 → scaled to 1000 on merge
nerd_lite:
  family_name: "SarasaMonoTCEmojiLiteNerd"
  nerd_font: "NerdFontsSymbolsOnly/SymbolsNerdFontMono-Regular.ttf"
  output_dir: "output/fonts-nerd-lite"
  description: "Sarasa Mono TC with Noto Emoji (monochrome) + Nerd Fonts PUA icons"
  # BMP PUA ranges to include. Format: [start, end] (inclusive, hex int).
  # Only codepoints in these ranges will be imported from the Nerd font.
  icon_ranges:
    - [0xE0A0, 0xE0D7]   # Powerline Symbols
    - [0xE5FA, 0xE6FF]   # Seti-UI + Custom
    - [0xE700, 0xE7FF]   # Devicons
    - [0xEA60, 0xEBEB]   # Codicons
    - [0xF400, 0xF4FF]   # Octicons
```

注意事項：
- `nerd_font` 路徑相對於 `fonts_dir`（即 `fonts/`）
- `icon_ranges` 格式為 `[start, end]` 整數對（與 `priority_codepoints` 的 `U+XXXX` 字串不同）

---

## Phase 2：build.py 新增 `--nerd-lite` 旗標 `[Copilot]`

### 2.1 import 新增

```python
from src.emoji_merge import merge_emoji, merge_emoji_lite, merge_emoji_lite_nerd, merge_emoji_colrv1, detect_font_widths, _strip_mac_name_records
```

### 2.2 argparse 新增

在 `--colrv1` argument 定義之後新增：

```python
parser.add_argument(
    "--nerd-lite",
    action="store_true",
    help="Build Nerd Lite variant (glyf emoji + Nerd Fonts PUA icons)",
)
```

### 2.3 互斥檢查

與 `--lite` / `--colrv1` 互斥，擴充現有互斥判斷：

```python
if sum([args.lite, args.colrv1, args.nerd_lite]) > 1:
    print("Error: --lite, --colrv1, and --nerd-lite are mutually exclusive")
    sys.exit(1)
```

### 2.4 variant 路由

在 `is_lite = args.lite` 附近新增：

```python
is_nerd_lite = args.nerd_lite
```

在讀取 family_name / output_dir / emoji_font 的 if/elif 鏈中，新增 `elif is_nerd_lite:` 分支，
讀取 `config.yaml` 的 `nerd_lite.*` 欄位（參照 `lite:` 分支的寫法）。

### 2.5 build_single_font 呼叫

在 `build_single_font()` 呼叫點，`lite=is_lite` 之後加入 `nerd_lite=is_nerd_lite`，
並在 `build_single_font()` 函式簽章與內部邏輯中新增對應的 `nerd_lite: bool = False` 參數。

`build_single_font()` 內部路由：

```python
if nerd_lite:
    merged_font = merge_emoji_lite_nerd(
        base_font_path=str(base_font_path),
        emoji_font_path=str(variant_emoji_font_path),
        nerd_font_path=str(nerd_font_path),   # 由呼叫端傳入
        config=font_config,
        icon_ranges=icon_ranges,               # list[tuple[int,int]]，由 config 解析
    )
```

---

## Phase 3：src/emoji_merge.py 核心實作 `[Claude]`

### 3.1 新增輔助函式：`_load_nerd_pua_glyphs()`

**位置**：在 `_scale_glyph()` 定義之後（約 line 555）

```python
def _load_nerd_pua_glyphs(
    nerd_font: TTFont,
    icon_ranges: list[tuple[int, int]],
) -> dict[int, str]:
    """
    從 Nerd Font 的 cmap 中，依照 icon_ranges 過濾出 BMP PUA 碼位。

    Returns:
        {codepoint: glyph_name} 的子集合 dict
    """
```

實作要點：
- 使用 `nerd_font.getBestCmap()` 取得完整 cmap
- 僅保留 codepoint 落在任一 `icon_ranges` 範圍內的項目
- 結果以 codepoint 升序排列（利於 debug log）

### 3.2 新增核心函式：`_merge_nerd_fonts_pua()`

**位置**：在 `_load_nerd_pua_glyphs()` 之後

```python
def _merge_nerd_fonts_pua(
    base_font: TTFont,
    nerd_font: TTFont,
    pua_glyphs: dict[int, str],   # 來自 _load_nerd_pua_glyphs()
    half_width: int,
    upm_scale: float,             # = base_font UPM / nerd_font UPM = 1000 / 2048
) -> list[int]:
    """
    將 Nerd Font PUA glyph 合併進 base_font。

    對每個 (codepoint, glyph_name)：
      1. 若 codepoint 已在 base_font cmap 中 → 跳過（不覆蓋）
      2. 從 nerd_font['glyf'] 複製 glyph
      3. 用 _scale_glyph(glyph, upm_scale) 縮放
      4. 計算縮放後的 lsb（glyph.xMin）
      5. 設定 advance width = half_width（PUA icon 佔 1 欄）
      6. 更新 base_font['glyf']、['hmtx']、glyph order、cmap

    Returns:
        成功合併的 codepoint list（供 caller 做 log / test）
    """
```

**關鍵實作細節**：

a) **UPM 縮放**：直接複用現有 `_scale_glyph(glyph, upm_scale)`；
   注意 Nerd Fonts 可能有 composite glyph（`numberOfContours == -1`），
   需確認 `_scale_glyph()` 是否正確處理 composite 的 `dx/dy` component offset。

b) **lsb 計算**：縮放後 `lsb = glyph.xMin`（若 glyph 有 `xMin` 屬性）；
   simple glyph 縮放後 fonttools 會自動更新 `xMin`，但需確認 `recalcBBoxes` 設定。

c) **advance width**：Nerd icon 佔 **1 欄**（half_width = 500），
   不同於 emoji 的 2 欄（emoji_width = 1000）。

d) **glyph name**：直接使用 Nerd font 的原始 glyph name（如 `uniE0A0`）；
   若名稱衝突（不太可能但需防範），加 `_nerd` suffix。

e) **cmap 更新**：直接呼叫現有 `_update_cmap(base_font, {cp: glyph_name})`。

f) **post table**：若 base_font 為 post format 3.0，合併後需確認 glyph name 能持久化；
   視情況升級至 format 2.0（參照 Color forced rename 的 Step 9.5 做法）。

### 3.3 新增入口函式：`merge_emoji_lite_nerd()`

**位置**：在 `merge_emoji_lite()` 之後

函式簽章：

```python
def merge_emoji_lite_nerd(
    base_font_path: str,
    emoji_font_path: str,
    nerd_font_path: str,
    config: FontConfig,
    icon_ranges: list[tuple[int, int]],
    force_codepoints: set[int] | None = None,
) -> TTFont:
```

實作策略：

1. 先呼叫 `merge_emoji_lite(...)` 取得含 emoji 的 merged font（**重用整個 Lite pipeline**）
2. 接著開啟 nerd_font，呼叫 `_load_nerd_pua_glyphs()` + `_merge_nerd_fonts_pua()`
3. 更新 family name → `SarasaMonoTCEmojiLiteNerd`（呼叫現有 `_update_font_name_table()`）

這樣的設計優點：
- 不複製 `merge_emoji_lite()` 的 1,000+ 行邏輯
- Lite 的所有功能（flag poc、sequence、BMP force）完全繼承
- Nerd merge 是獨立的後處理步驟，容易 debug / 隔離

---

## Phase 4：測試 `[Copilot + Claude]`

### 4.1 Smoke test `[Copilot]`

在 `tests/test_font_output.py` 新增 `test_nerd_lite_output_*` class 或 fixture：

```python
# Copilot 補充：build 成功 + 輸出檔存在
def test_nerd_lite_output_exists():
    # 確認 output/fonts-nerd-lite/SarasaMonoTCEmojiLiteNerd-Regular.ttf 存在

def test_nerd_lite_family_name():
    # 確認 name table family name = "SarasaMonoTCEmojiLiteNerd"

def test_nerd_lite_pua_in_cmap():
    # 確認 E0A0（Powerline）、E700（Devicons）等代表碼位在 cmap 中
```

### 4.2 Glyph quality regression test `[Claude]`

```python
def test_nerd_lite_pua_advance_width():
    # 確認 PUA glyph advance width = half_width（500），而非 emoji_width（1000）

def test_nerd_lite_pua_glyph_bbox_sane():
    # 確認縮放後 glyph bbox 在合理範圍內（不超出 UPM 上下界）

def test_nerd_lite_no_emoji_cmap_overlap():
    # 確認 emoji 碼位（U+1F600 等）不被 PUA merge 覆蓋
```

---

## Phase 5：verify-emoji.html 新增 Nerd 區塊 `[Claude]`

在現有 Lite / Section 11（非 Regular 對比）之後新增 Section 12：

- 載入 `SarasaMonoTCEmojiLiteNerd-Regular.ttf`（使用 FontFace API，路徑 `/output/fonts-nerd-lite/...`）
- 展示代表性 PUA icon：
  - Powerline 分隔符（E0B0、E0B2）、branch symbol（E0A0）
  - 幾個語言 logo（Python E73C、JS E74E、Go E724、Rust E7A8）
  - VS Code Codicons 樣本
  - Octicons 樣本（git branch、PR、issue）
- 與 Lite 版本並排對比（中文 / emoji 不應受影響）

---

## Phase 6：文件更新 `[Copilot]`

### 6.1 `.github/copilot-instructions.md`

在「三種變體」表格後方加入第四列：
```
| **Nerd Lite** | `SarasaMonoTCEmojiLiteNerd` | glyf TrueType + Nerd PUA | 終端機 icon、VHS 錄影含 Nerd icon |
```

在「Lite 特有」段落之後新增「Nerd Lite 特有」段落：
- 來源字體：`SymbolsNerdFontMono-Regular.ttf`，UPM 2048
- UPM 縮放：2048 → 1000（scale factor ≈ 0.4883）
- PUA icon advance width = half_width（1 欄，非 2 欄 emoji）
- 設定位置：`config.yaml` → `nerd_lite.icon_ranges`
- pipeline：先執行完整 `merge_emoji_lite()`，再做 Nerd PUA 後處理

### 6.2 README.md

在「三種輸出變體」表格後加入 Nerd Lite 列（MVP 完成後補充實際數據）。

新增指令說明：
```bash
uv run python build.py --nerd-lite                    # Nerd Lite 變體
uv run python build.py --nerd-lite --styles Regular   # 快速單樣式測試
```

---

## 驗收條件

| 項目 | 驗收標準 |
|------|---------|
| Build 成功 | `uv run python build.py --nerd-lite --styles Regular` 無 error |
| 輸出檔存在 | `output/fonts-nerd-lite/SarasaMonoTCEmojiLiteNerd-Regular.ttf` |
| Family name | name table ID 1 = `SarasaMonoTCEmojiLiteNerd` |
| PUA cmap | E0A0 / E700 / EA60 / F400 / E5FA 各至少一個代表碼位在 cmap |
| Emoji 正常 | 👩‍💻 / 👋🏻 / 🇺🇸 在 cmap 且 GSUB ligature 存在 |
| 字寬一致 | PUA glyph advance width = 500；emoji glyph advance width = 1000 |
| 視覺確認 | verify-emoji.html Section 12 顯示正確 icon + emoji + 中文 |
| 測試通過 | `uv run pytest tests/ -v --tb=short` 全綠 |

---

## 風險提醒（給 Claude Code）

| 風險 | 位置 | 注意事項 |
|------|------|---------|
| Composite glyph | `_scale_glyph()` / `_merge_nerd_fonts_pua()` | 確認 Nerd font 有多少 composite glyph；`_scale_glyph()` 可能需補 composite `dx/dy` 縮放 |
| lsb 計算 | `_merge_nerd_fonts_pua()` | `recalcBBoxes=False` 時需手動計算 `xMin` |
| post table 升級 | `merge_emoji_lite_nerd()` | Sarasa post format 3.0；若需持久化 PUA glyph 名稱，需升級至 2.0 |
| advance width 1 vs 2 | `_merge_nerd_fonts_pua()` | PUA icon 佔 1 欄（half_width）；不要沿用 emoji 的 emoji_width |
| 合併順序 | `merge_emoji_lite_nerd()` | 先 Lite emoji merge，後 Nerd PUA；若順序反了，Lite flag poc helper glyph 可能與 PUA name 衝突 |

---

## 不在 MVP 範圍

- Bold / Italic / BoldItalic（Phase 2 評估後決定）
- Plane 15 PUA（Material Design Icons）
- Font Awesome（數量大，Phase 2 評估）
- Color 或 COLRv1 變體加入 Nerd merge
- Nerd Fonts PUA 的優先/force 機制（先全量選取，未來再調整）
