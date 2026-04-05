# SarasaMonoTC-Emoji

[![Tests](https://github.com/sspig0127/SarasaMonoTC-Emoji/actions/workflows/test.yml/badge.svg)](https://github.com/sspig0127/SarasaMonoTC-Emoji/actions/workflows/test.yml)
[![Release](https://github.com/sspig0127/SarasaMonoTC-Emoji/actions/workflows/release.yml/badge.svg)](https://github.com/sspig0127/SarasaMonoTC-Emoji/actions/workflows/release.yml)

**Sarasa Mono TC（更紗黑體繁中等寬）+ Emoji — 嵌入式 emoji，支援四種變體**

## v2.2 重點

- **COLRv1 budget 擴增**：收錄量由 629 提升到 **811**（540 單碼 emoji + 271 sequences）
- `max_new_glyphs` 提高至 8,450；實際消耗 8,327（剩餘 123 slots 緩衝）
- greedy 選取改為 **skip-and-continue**，不再在第一個超預算 emoji 停止
- 新增 10 個 priority emoji：📏 📐 📝 📜 📕 📗 📘 📙 📔 🕑
- 新增 221 個 priority sequences（膚色變體 / ZWJ / 旗幟）

v2.1 起支援 sequence emoji（ZWJ / 膚色 / 旗幟），四個變體（`Color` / `Lite` / `COLRv1` / `Nerd Lite`）全部接通。

相關技術文件：
- [`ROADMAP.md`](ROADMAP.md) — 版本規劃與維護追蹤
- [`docs/roadmap-history.md`](docs/roadmap-history.md) — 歷史版本實作細節
- [`docs/v2-sequence-implementation.md`](docs/v2-sequence-implementation.md) — v2.0 sequence emoji 實作設計
- [`.github/colrv1-dev-notes.md`](.github/colrv1-dev-notes.md) — COLRv1 深度技術筆記

## 變體說明

| 變體 | 字族名稱 | Emoji 格式 | 大小 | 適用場景 |
|------|----------|------------|------|----------|
| **Color**（彩色） | `SarasaMonoTCEmoji` | CBDT/CBLC 彩色點陣圖 | ~35 MB | 日常終端機、編輯器 |
| **Lite**（單色） | `SarasaMonoTCEmojiLite` | glyf TrueType outline | ~25 MB | VHS 錄影、輕量部署 |
| **COLRv1**（彩色向量） | `SarasaMonoTCEmojiCOLRv1` | COLRv1 向量 paint tree | ~26 MB | Chrome/Chromium 終端機 |
| **Nerd Lite**（單色 + PUA icon） | `SarasaMonoTCEmojiLiteNerd` | glyf TrueType outline + Nerd Fonts BMP PUA | ~26 MB | 終端機 icon、VHS 錄影、單字體部署 |

四個變體可同時安裝，不互相衝突。

---

## 下載字體

前往 [Releases](https://github.com/sspig0127/SarasaMonoTC-Emoji/releases) 下載最新版本。

### Color 變體

| 檔案 | 說明 |
|------|------|
| `SarasaMonoTCEmoji-Regular.ttf` | 一般 |
| `SarasaMonoTCEmoji-Italic.ttf` | 斜體 |
| `SarasaMonoTCEmoji-Bold.ttf` | 粗體 |
| `SarasaMonoTCEmoji-BoldItalic.ttf` | 粗斜體 |

### Lite 變體

| 檔案 | 說明 |
|------|------|
| `SarasaMonoTCEmojiLite-Regular.ttf` | 一般 |
| `SarasaMonoTCEmojiLite-Italic.ttf` | 斜體 |
| `SarasaMonoTCEmojiLite-Bold.ttf` | 粗體 |
| `SarasaMonoTCEmojiLite-BoldItalic.ttf` | 粗斜體 |

### COLRv1 變體

> Chrome/Chromium 98+ 原生支援，彩色向量可縮放，比 Color 小 26%

| 檔案 | 說明 |
|------|------|
| `SarasaMonoTCEmojiCOLRv1-Regular.ttf` | 一般 |
| `SarasaMonoTCEmojiCOLRv1-Italic.ttf` | 斜體 |
| `SarasaMonoTCEmojiCOLRv1-Bold.ttf` | 粗體 |
| `SarasaMonoTCEmojiCOLRv1-BoldItalic.ttf` | 粗斜體 |

### Nerd Lite 變體

> 以 Lite 變體為底，再合併 Nerd Fonts BMP PUA icon，讓單一字體同時具備中文、emoji 與常用開發圖示。
> Powerline（E0A0–E0D7）1 欄，Devicons / Codicons / Octicons / Seti-UI 2 欄。

| 檔案 | 說明 |
|------|------|
| `SarasaMonoTCEmojiLiteNerd-Regular.ttf` | 一般 |
| `SarasaMonoTCEmojiLiteNerd-Italic.ttf` | 斜體 |
| `SarasaMonoTCEmojiLiteNerd-Bold.ttf` | 粗體 |
| `SarasaMonoTCEmojiLiteNerd-BoldItalic.ttf` | 粗斜體 |

下載所需字重的 `.ttf` 檔案，雙擊安裝即可。

---

## 背景

[Sarasa Gothic](https://github.com/be5invis/Sarasa-Gothic) 是優秀的 CJK 等寬字體，
但作者明確表示不加入 emoji 支援（[Issue #82](https://github.com/be5invis/Sarasa-Gothic/issues/82)）：

> *"Sarasa is not, and never, designed for displaying Emoji"*

### 現有替代方案的侷限

| 方案 | 問題 |
|------|------|
| [jonz94/Sarasa-Gothic-Nerd-Fonts](https://github.com/jonz94/Sarasa-Gothic-Nerd-Fonts) | 只有單色 NerdFont 圖示，無彩色 emoji |
| [thedemons/merge_color_emoji_font](https://github.com/thedemons/merge_color_emoji_font) | 只有 FontLab GUI 手動教學，非 Sarasa，不自動化 |
| OS fallback（fontconfig / VSCode font stack） | 無法保證等寬對齊，在所有環境下不一致 |

**本專案**是首個用 Python/fonttools 自動化將 emoji 嵌入 Sarasa Mono TC 的方案。

---

## 字體來源與授權

### 來源字體對應

#### Color 變體

| 字體 | 來源 | 授權 |
|------|------|------|
| Sarasa Mono TC | [be5invis/Sarasa-Gothic](https://github.com/be5invis/Sarasa-Gothic) | SIL OFL 1.1 |
| NotoColorEmoji | [googlefonts/noto-emoji](https://github.com/googlefonts/noto-emoji) | SIL OFL 1.1 |
| **SarasaMonoTCEmoji（本專案）** | 衍生作品 | SIL OFL 1.1 |

#### Lite 變體

| 字體 | 來源 | 授權 |
|------|------|------|
| Sarasa Mono TC | [be5invis/Sarasa-Gothic](https://github.com/be5invis/Sarasa-Gothic) | SIL OFL 1.1 |
| Noto Emoji（單色）| [google/fonts ofl/notoemoji](https://github.com/google/fonts/tree/main/ofl/notoemoji) | SIL OFL 1.1 |
| **SarasaMonoTCEmojiLite（本專案）** | 衍生作品 | SIL OFL 1.1 |

#### COLRv1 變體

| 字體 | 來源 | 授權 |
|------|------|------|
| Sarasa Mono TC | [be5invis/Sarasa-Gothic](https://github.com/be5invis/Sarasa-Gothic) | SIL OFL 1.1 |
| Noto COLRv1 | [googlefonts/noto-emoji](https://github.com/googlefonts/noto-emoji) | SIL OFL 1.1 |
| **SarasaMonoTCEmojiCOLRv1（本專案）** | 衍生作品 | SIL OFL 1.1 |

#### Nerd Lite 變體

| 字體 | 來源 | 授權 |
|------|------|------|
| Sarasa Mono TC | [be5invis/Sarasa-Gothic](https://github.com/be5invis/Sarasa-Gothic) | SIL OFL 1.1 |
| Noto Emoji（單色）| [google/fonts ofl/notoemoji](https://github.com/google/fonts/tree/main/ofl/notoemoji) | SIL OFL 1.1 |
| Nerd Fonts Symbols Only | [ryanoasis/nerd-fonts](https://github.com/ryanoasis/nerd-fonts) | MIT |
| **SarasaMonoTCEmojiLiteNerd（本專案）** | 衍生作品 | SIL OFL 1.1 |

### 授權說明

本專案發行的字體檔案均為衍生作品，整體遵循 **SIL Open Font License 1.1**（[完整條文](LICENSE)）。Nerd Fonts 來源字體採 MIT 授權，合併後的衍生字體以 OFL 發行。

#### SIL OFL 1.1 允許

| 行為 | 說明 |
|------|------|
| ✅ 個人與商業使用 | 可用於任何用途，包含商業軟體、產品 |
| ✅ 自由修改 | 可修改字形、字距、合併其他字體 |
| ✅ 再發行 | 可重新發布原版或修改版，但須保留授權條文 |
| ✅ 與軟體捆綁 | 可嵌入應用程式、IDE、終端機模擬器等一同發行 |

#### SIL OFL 1.1 不允許

| 行為 | 說明 |
|------|------|
| ❌ 單獨販售字體 | 不可將字體本身作為獨立商品出售（可作為軟體的一部分收費） |
| ❌ 使用保留字型名稱 | 衍生作品不可使用原字體的保留名稱（本專案已使用不同名稱 `SarasaMonoTCEmoji`） |

---

## Emoji 版本對應

Emoji 標準由 Unicode Consortium 維護（[UTS #51](https://unicode.org/reports/tr51/)），每年 9 月發布新版本。

| Emoji 版本 | 對應 Unicode | 發布日期 |
|------------|--------------|----------|
| Emoji 15.0 | Unicode 15.0 | 2022-09 |
| Emoji 15.1 | Unicode 15.1 | 2023-09 |
| Emoji 16.0 | Unicode 16.0 | 2024-09 |
| **Emoji 17.0** | Unicode 17.0 | 2025-09（目前最新） |

更新依據：
- **Color 變體**：追蹤 `googlefonts/noto-emoji` releases → 更新 `fonts/NotoColorEmoji.ttf`
- **Lite 變體**：追蹤 `google/fonts` 的 `ofl/notoemoji/` → 更新 `fonts/NotoEmoji[wght].ttf`
- **COLRv1 變體**：追蹤 `googlefonts/noto-emoji` main → 更新 `fonts/Noto-COLRv1.ttf`

---

## Nerd Fonts 版本對應

Nerd Fonts 由 [ryanoasis/nerd-fonts](https://github.com/ryanoasis/nerd-fonts) 維護，不定期發布新版本。
本專案使用 **Symbols Only** 子集（僅含 PUA icon，無拉丁字元），授權 MIT。

| Nerd Fonts 版本 | 說明 |
|-----------------|------|
| **3.4.0**（目前使用） | 目前建構預設版本；[下載 NerdFontsSymbolsOnly.zip](https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/NerdFontsSymbolsOnly.zip) |
| 3.x（持續更新） | 部分 icon codepoint 已遷移至新 PUA 段（如 Material Design Icons），建議每次 release 前確認 |

**更新方式：**

1. 前往 [Nerd Fonts Releases](https://github.com/ryanoasis/nerd-fonts/releases)，下載新版 `NerdFontsSymbolsOnly.zip`
2. 解壓取出 `SymbolsNerdFontMono-Regular.ttf`，替換 `fonts/NerdFontsSymbolsOnly/SymbolsNerdFontMono-Regular.ttf`
3. 更新 `config.yaml` 的備註版本號（或 release workflow 的 `nerd_fonts_version` 預設值）
4. 重跑測試與 Nerd Lite 建構：`uv run pytest tests/ && uv run python build.py --nerd-lite`

> ⚠️ Nerd Fonts 不保證 icon codepoint 穩定；升版後建議用 `verify-emoji.html` 目視確認 PUA icon 是否位移

---

## 自行建構

### 下載源字體

> **自動搜尋**：build script 會自動在 `fonts/` 及其子目錄內搜尋所需字體檔案。
> 下載後直接解壓縮放入 `fonts/`，**不需要手動把 TTF 拖出來**。

#### 1. Sarasa Mono TC（4 個 TTF）

前往 [Sarasa Gothic releases](https://github.com/be5invis/Sarasa-Gothic/releases) 下載最新版的：

```
sarasa-mono-tc-ttf-{version}.7z
```

解壓後將整個資料夾放入 `fonts/`（或直接把 TTF 放在 `fonts/` 根目錄皆可）：

```
fonts/
└── SarasaMonoTC-TTF-{version}/     ← 整個解壓資料夾直接放入即可
    ├── SarasaMonoTC-Regular.ttf
    ├── SarasaMonoTC-Italic.ttf
    ├── SarasaMonoTC-Bold.ttf
    └── SarasaMonoTC-BoldItalic.ttf
```

#### 2. NotoColorEmoji（Color 變體用）

前往 [noto-emoji releases](https://github.com/googlefonts/noto-emoji/releases) 下載，放入 `fonts/`：

```
fonts/NotoColorEmoji.ttf
```

#### 3. Noto Emoji（Lite 變體用）

下載單色 variable font，放入 `fonts/`：

```bash
curl -L -o fonts/NotoEmoji\[wght\].ttf \
  "https://github.com/google/fonts/raw/main/ofl/notoemoji/NotoEmoji%5Bwght%5D.ttf"
```

#### 4. Noto COLRv1（COLRv1 變體用）

前往 [noto-emoji fonts/](https://github.com/googlefonts/noto-emoji/blob/main/fonts/) 下載，放入 `fonts/`：

```
fonts/Noto-COLRv1.ttf
```

#### 5. Symbols Nerd Font Mono（Nerd Lite 變體用）

前往 [Nerd Fonts Releases](https://github.com/ryanoasis/nerd-fonts/releases)，下載 `NerdFontsSymbolsOnly.zip`，
解壓後將整個資料夾（或 TTF 檔案）放入 `fonts/`：

```
fonts/
└── NerdFontsSymbolsOnly/           ← 解壓資料夾直接放入即可
    └── SymbolsNerdFontMono-Regular.ttf
```

> 目前預設版本：[v3.4.0](https://github.com/ryanoasis/nerd-fonts/releases/download/v3.4.0/NerdFontsSymbolsOnly.zip)（MIT 授權）

### 建構

```bash
# 安裝依賴
uv sync

# Color 變體（彩色，CBDT/CBLC）
uv run python build.py

# Lite 變體（單色 glyf，VHS 相容）
uv run python build.py --lite

# COLRv1 變體（彩色向量，Chrome 98+）
uv run python build.py --colrv1

# Nerd Lite 變體（Lite emoji + Nerd Fonts PUA icon）
uv run python build.py --nerd-lite

# 只建構 Regular（快速測試）
uv run python build.py --styles Regular
uv run python build.py --lite --styles Regular
uv run python build.py --colrv1 --styles Regular
uv run python build.py --nerd-lite --styles Regular
```

### 自動發佈 Workflow

GitHub Actions 提供手動觸發的完整建構與發佈流程（`.github/workflows/release.yml`），
不需要在本機執行三段建構與 zip 打包。

**觸發方式：** GitHub repo → Actions → **Build and Release** → Run workflow

| 輸入參數 | 說明 | 預設值 |
|----------|------|--------|
| `release_tag` | 發佈標籤（如 `v2.2.0`） | 必填 |
| `sarasa_version` | Sarasa Gothic 版本號 | `1.0.36` |
| `nerd_fonts_version` | Nerd Fonts 版本號（Symbols Only） | `3.4.0` |

**執行流程：** 下載來源字體 → 執行 134 個測試 → 建構四種變體 → 打包 zip → 上傳至指定 Release

- 若 Release 已存在：以 `--clobber` 覆蓋現有附件
- 若 Release 不存在：建立 draft release，由維護者手動 publish

**Draft release publish 方式（二擇一）：**

**方法1： CLI（推薦）**

```bash
gh release edit <tag> --draft=false
```

**方法2：GitHub 網頁**
到 GitHub 網頁：Releases → 找到該 draft → Edit → 點擊 **Publish release**


---

### 輸出

```
output/
├── fonts/                               # Color 變體
│   ├── SarasaMonoTCEmoji-Regular.ttf
│   ├── SarasaMonoTCEmoji-Italic.ttf
│   ├── SarasaMonoTCEmoji-Bold.ttf
│   ├── SarasaMonoTCEmoji-BoldItalic.ttf
│   └── fonts-manifest.json
├── fonts-lite/                          # Lite 變體
│   ├── SarasaMonoTCEmojiLite-Regular.ttf
│   ├── SarasaMonoTCEmojiLite-Italic.ttf
│   ├── SarasaMonoTCEmojiLite-Bold.ttf
│   ├── SarasaMonoTCEmojiLite-BoldItalic.ttf
│   └── fonts-manifest.json
├── fonts-colrv1/                        # COLRv1 變體
│   ├── SarasaMonoTCEmojiCOLRv1-Regular.ttf
│   ├── SarasaMonoTCEmojiCOLRv1-Italic.ttf
│   ├── SarasaMonoTCEmojiCOLRv1-Bold.ttf
│   ├── SarasaMonoTCEmojiCOLRv1-BoldItalic.ttf
│   └── fonts-manifest.json
└── fonts-nerd-lite/                     # Nerd Lite 變體
    ├── SarasaMonoTCEmojiLiteNerd-Regular.ttf
    ├── SarasaMonoTCEmojiLiteNerd-Italic.ttf
    ├── SarasaMonoTCEmojiLiteNerd-Bold.ttf
    ├── SarasaMonoTCEmojiLiteNerd-BoldItalic.ttf
    └── fonts-manifest.json

docs/
└── colrv1-emoji-list.json               # COLRv1 greedy 選取清單（含 codepoint、unicode name、glyph cost）
```

---

## 驗證

```bash
# Color 變體驗證
uv run python -c "
from fontTools.ttLib import TTFont
f = TTFont('output/fonts/SarasaMonoTCEmoji-Regular.ttf')
assert 'CBDT' in f and 'CBLC' in f, 'Missing color tables'
cmap = f['cmap'].getBestCmap()
for cp, name in [(0x1F600, '😀'), (0x1F525, '🔥'), (0x4E00, '一')]:
    assert cp in cmap, f'Missing U+{cp:04X} {name}'
print(f'OK — Total glyphs: {len(f.getGlyphOrder())}')
"

# Lite 變體驗證
uv run python -c "
from fontTools.ttLib import TTFont
f = TTFont('output/fonts-lite/SarasaMonoTCEmojiLite-Regular.ttf')
assert 'glyf' in f and 'CBDT' not in f, 'Should have glyf, no CBDT'
cmap = f['cmap'].getBestCmap()
for cp, name in [(0x1F600, '😀'), (0x1F525, '🔥'), (0x4E00, '一')]:
    assert cp in cmap, f'Missing U+{cp:04X} {name}'
print(f'OK — Total glyphs: {len(f.getGlyphOrder())}')
"

# COLRv1 變體驗證
uv run python -c "
from fontTools.ttLib import TTFont
f = TTFont('output/fonts-colrv1/SarasaMonoTCEmojiCOLRv1-Regular.ttf')
assert 'COLR' in f and 'CPAL' in f, 'Missing COLR/CPAL tables'
assert 'CBDT' not in f, 'Should not have CBDT'
cmap = f['cmap'].getBestCmap()
for cp, name in [(0x1F600, '😀'), (0x1F525, '🔥'), (0x4E00, '一')]:
    assert cp in cmap, f'Missing U+{cp:04X} {name}'
print(f'OK — Total glyphs: {len(f.getGlyphOrder())}')
"

# 瀏覽器目視驗證
uv run python -m http.server 8765
open http://localhost:8765/verify-emoji.html
停止伺服器：

**前景執行時：** 回到啟動伺服器的終端機視窗，按 `Ctrl+C` 即可。

**背景執行時：** 若已把伺服器放到後台（例如執行 `uv run python -m http.server 8765 &`），先查出進程 ID（PID）：

```bash
lsof -i :8765
```

輸出類似：
```
COMMAND   PID  USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
python  12345   mac    3u  IPv4 0x1234567890abcdef      0t0  TCP localhost:8765 (LISTEN)
```

然後結束該進程：

```bash
kill 12345
```

或直接用一行指令強制結束佔用該 port 的進程：

```bash
lsof -ti :8765 | xargs kill -9
```

`verify-emoji.html` 目前已包含：
- 來源字體 vs 合併後字體對照
- COLRv1 高風險樣本區（大量 `PaintTransform -> PaintGlyph` 案例）
- font URL cache-busting，避免瀏覽器沿用舊字體快取

---

## 測試（開發用）

```bash
# uv sync 已包含 pytest（dependency-groups.dev）
uv sync

# 執行全部測試
uv run pytest tests/ -v

# 只跑不需要字體檔案的純邏輯測試（CI 亦執行此組）
uv run pytest tests/test_emoji_merge.py::TestScaleGlyph -v
```

| 測試組 | 所需檔案 | 執行環境 |
|--------|----------|----------|
| 純邏輯測試（config / scale / cmap / filter） | 無 | 本機 / CI |
| Noto Emoji 依賴測試（`get_emoji_cmap` / `collect_glyph_deps`） | `fonts/NotoEmoji[wght].ttf` | 本機 / CI（自動下載） |
| Noto COLRv1 依賴測試（`TestCollectColrv1Deps`） | `fonts/Noto-COLRv1.ttf` | 僅本機 |
| Sarasa 依賴測試（`TestDetectFontWidths`） | `fonts/SarasaMonoTC-Regular.ttf` | 僅本機 |
| output font 驗證（Color / Lite / COLRv1） | 已建構的 `output/` 字體 | 僅本機 |

字體檔案不存在時，相關測試自動 skip（不算失敗）。

---

## VHS 終端機錄影設定

[VHS](https://github.com/charmbracelet/vhs) 使用 Headless Chromium + xterm.js 渲染終端機畫面，
需使用 **Lite 變體**（glyf 格式）才能正確顯示 emoji（Color 變體的 CBDT/CBLC 點陣圖在 Chromium 中支援不穩定）。

如果你的首要目標是：
- VHS 錄影
- xterm.js / Headless Chromium
- 無法控制系統 emoji fallback 的終端機或嵌入環境

建議把 **Lite** 視為主要產品線。`COLRv1` 目前更適合「想保留彩色 emoji、且宿主 renderer 已知支援 COLRv1」的環境，
不建議當作 VHS / fallback-sensitive workflow 的唯一依賴。

### 4K 錄製設定參考(字體大小大約40~48)

```tape
Set Theme "Catppuccin Mocha"
Set FontFamily "SarasaMonoTCEmojiLite"
Set FontSize 48
Set LetterSpacing 0
Set LineHeight 1.2
Set Width 3840
Set Height 2160
```

---

## 技術細節

### Color 變體
- **Emoji 格式**：CBDT/CBLC（NotoColorEmoji 的彩色點陣圖格式）
- **Emoji 寬度**：Runtime 偵測 Sarasa 的 half-width，emoji = 2× half-width（與 CJK 等寬）
- **BMP 彩色覆蓋**：❤ ⭐ ⚠ ☺ ⚡ 等 BMP 符號預設使用 NotoColorEmoji 彩色點陣圖，
  而非 Sarasa 原有單色字形（可透過 `config.yaml` 的 `emoji.force_color_codepoints` 自訂清單）

### Lite 變體
- **Emoji 格式**：glyf TrueType outline（Noto Emoji variable font 的預設字重）
- **檔案大小**：比 Color 變體約小 30%（無點陣圖資料）
- **渲染**：Emoji 以終端機前景色顯示（單色），完整支援 Chromium/xterm.js
- **Sequence 支援**：已支援 ZWJ / 膚色 / 旗幟，透過輸出字體中的 GSUB ligature 規則實作
- **定位**：目前最適合 VHS、終端機錄影、以及無法信任系統 fallback 行為的環境
- **旗幟設計**：所有標準 Regional Indicator 雙碼旗幟序列一律套用 2-column 自訂旗面設計（共享旗面模板 + 壓縮字母組件），視覺上維持 2 columns 且提升辨識度
- **已知限制**：Lite 旗幟以單色 outline 顯示，無法重現 Color / COLRv1 的彩色旗面。若需要彩色旗幟，應優先使用 Color / COLRv1 變體

### COLRv1 變體
- **Emoji 格式**：COLRv1 paint tree（OpenType Color Font Version 1）
- **Emoji 數量**：540 個 emoji（codepoint 映射）+ 271 個 sequence ligatures（glyph 預算上限 8,450 slots），採兩階段選取：
  1. **Priority 優先**：52 個 priority / forced emoji + 221 個 priority sequences 先保證選入
  2. **Greedy 填充**：剩餘預算依 codepoint 升序掃描，超預算者 skip 繼續（skip-and-continue）
  - 完整選取清單：[`docs/colrv1-emoji-list.json`](docs/colrv1-emoji-list.json)
  - 可透過 `config.yaml` 的 `colrv1.max_new_glyphs` 調整預算
  - 可透過 `config.yaml` 的 `colrv1.priority_codepoints` 自訂優先 emoji 清單
  - 可透過 `config.yaml` 的 `colrv1.priority_sequences` 自訂高價值 sequence 清單
- **BMP 彩色覆蓋**：❤ ⭐ ⚠ ☺ ⚡ 等 BMP 符號可透過 `config.yaml` 的 `colrv1.force_colrv1_codepoints`
  強制使用 COLRv1 向量著色，取代 Sarasa 原有單色字形
- **Sequence 支援**：已支援 sequence emoji，但目前採剩餘 glyph budget 內的 priority / greedy 選取，不是全量 sequence 覆蓋
- **Priority 清單挑選依據**：
  - Greedy 填充以 codepoint 升序掃描，超預算者跳過繼續尋找更便宜的候選（v2.2 起 skip-and-continue）
  - ⚠️ ❌ ⭐ ➡️ ⚙️ 等 BMP 符號透過 `force_colrv1_codepoints` 單獨管理
  - Priority 清單選取標準：**在 GitHub README / Issues / PR / CI 表格中高頻出現**，且不在 Sarasa 原有 cmap 中
  - 涵蓋：工具類（🔧🔨🛠️）、安全類（🔒🔑🛡️）、狀態圓點（🔴🟡🟢🔵）、連結導覽（🔗🔍🔖）、動作類（🚀🎉🐛）等
- **技術**：7,507 個 geometry helper glyphs（PaintGlyph 節點引用）+ 811 個 glyf stub（540 單碼 + 271 sequences）；paint tree 驅動彩色渲染
- **Chromium 相容性重點**：除了縮放 COLR paint tree 的 font-unit 座標之外，geometry helper glyph 的 metrics 也必須保留來源字體縮放後的值；若 helper metrics 被清成 `(0, 0)`，🟡 / 🟢 這類高倍率 transform emoji 會只剩 tiny fragment
- **檔案大小**：~26 MB（比 Color 小 26%；COLRv1 向量資料比 PNG 點陣圖精簡）
- **支援環境**：Chrome/Chromium 98+、Firefox 107+；macOS 系統級支援需 macOS 13+
- **名稱衝突處理**：Sarasa 已有同名 glyph 時自動加 `_colrv1` 後綴（build log 會列出衝突數量）
- **定位**：適合現代瀏覽器 / GUI renderer 的彩色顯示；若以 VHS / xterm.js 穩定錄製為第一優先，仍應優先選 Lite

### 共同
- **Emoji 範圍**：單一 codepoint + sequence emoji（ZWJ / 膚色 / 旗幟）
- **工具**：純 Python + fonttools，無需 FontForge 或 FontLab
- **OTS 相容**：`recalcBBoxes=False` 保留 Sarasa 原始 glyph raw bytes，通過 OTS 9.2 驗證

---

## 授權

→ 完整說明見上方「[字體來源與授權 → 授權說明](#授權說明)」章節，以及 [LICENSE](LICENSE) 條文。
