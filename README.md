# SarasaMonoTC-Emoji

**Sarasa Mono TC（更紗黑體繁中等寬）+ Emoji — 嵌入式 emoji，支援彩色與單色兩種變體**

## 變體說明

| 變體 | 字族名稱 | Emoji 格式 | 適用場景 |
|------|----------|------------|----------|
| **Color**（彩色） | `SarasaMonoTCEmoji` | CBDT/CBLC 彩色點陣圖 | 日常終端機、編輯器 |
| **Lite**（單色） | `SarasaMonoTCEmojiLite` | glyf TrueType outline | VHS 錄影、輕量部署 |

兩個變體可同時安裝，不互相衝突。

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

### Color 變體

| 字體 | 來源 | 授權 |
|------|------|------|
| Sarasa Mono TC | [be5invis/Sarasa-Gothic](https://github.com/be5invis/Sarasa-Gothic) | SIL OFL 1.1 |
| NotoColorEmoji | [googlefonts/noto-emoji](https://github.com/googlefonts/noto-emoji) | SIL OFL 1.1 |
| **SarasaMonoTCEmoji（本專案）** | 衍生作品 | SIL OFL 1.1 |

### Lite 變體

| 字體 | 來源 | 授權 |
|------|------|------|
| Sarasa Mono TC | [be5invis/Sarasa-Gothic](https://github.com/be5invis/Sarasa-Gothic) | SIL OFL 1.1 |
| Noto Emoji（單色）| [google/fonts ofl/notoemoji](https://github.com/google/fonts/tree/main/ofl/notoemoji) | SIL OFL 1.1 |
| **SarasaMonoTCEmojiLite（本專案）** | 衍生作品 | SIL OFL 1.1 |

版權聲明：見 [LICENSE](LICENSE)

---

## Emoji 版本對應

Emoji 標準由 Unicode Consortium 維護（[UTS #51](https://unicode.org/reports/tr51/)），每年 9 月發布新版本。

| Emoji 版本 | 對應 Unicode | 發布日期 |
|------------|--------------|----------|
| Emoji 15.0 | Unicode 15.0 | 2022-09 |
| Emoji 15.1 | Unicode 15.1 | 2023-09 |
| **Emoji 16.0** | Unicode 16.0 | 2024-09（目前最新） |
| Emoji 17.0（預計） | Unicode 17.0 | 2025-09 |

更新依據：
- **Color 變體**：追蹤 `googlefonts/noto-emoji` releases → 更新 `fonts/NotoColorEmoji.ttf`
- **Lite 變體**：追蹤 `google/fonts` 的 `ofl/notoemoji/` → 更新 `fonts/NotoEmoji[wght].ttf`

---

## 自行建構

### 下載源字體

#### 1. Sarasa Mono TC（4 個 TTF）

前往 [Sarasa Gothic releases](https://github.com/be5invis/Sarasa-Gothic/releases) 下載最新版的：

```
sarasa-mono-tc-ttf-{version}.7z
```

解壓後將以下 4 個檔案放入 `fonts/`：

```
fonts/
├── SarasaMonoTC-Regular.ttf
├── SarasaMonoTC-Italic.ttf
├── SarasaMonoTC-Bold.ttf
└── SarasaMonoTC-BoldItalic.ttf
```

#### 2. NotoColorEmoji（Color 變體用）

前往 [noto-emoji releases](https://github.com/googlefonts/noto-emoji/releases) 下載：

```
NotoColorEmoji.ttf  →  放入 fonts/
```

#### 3. Noto Emoji（Lite 變體用）

下載單色 variable font：

```bash
curl -L -o fonts/NotoEmoji\[wght\].ttf \
  "https://github.com/google/fonts/raw/main/ofl/notoemoji/NotoEmoji%5Bwght%5D.ttf"
```

### 建構

```bash
# 安裝依賴
uv sync

# Color 變體（彩色，CBDT/CBLC）
uv run python build.py

# Lite 變體（單色 glyf，VHS 相容）
uv run python build.py --lite

# 只建構 Regular（快速測試）
uv run python build.py --styles Regular
uv run python build.py --lite --styles Regular
```

### 輸出

```
output/
├── fonts/                          # Color 變體
│   ├── SarasaMonoTCEmoji-Regular.ttf
│   ├── SarasaMonoTCEmoji-Italic.ttf
│   ├── SarasaMonoTCEmoji-Bold.ttf
│   ├── SarasaMonoTCEmoji-BoldItalic.ttf
│   └── fonts-manifest.json
└── fonts-lite/                     # Lite 變體
    ├── SarasaMonoTCEmojiLite-Regular.ttf
    ├── SarasaMonoTCEmojiLite-Italic.ttf
    ├── SarasaMonoTCEmojiLite-Bold.ttf
    ├── SarasaMonoTCEmojiLite-BoldItalic.ttf
    └── fonts-manifest.json
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

# 瀏覽器目視驗證
uv run python -m http.server 8765
open http://localhost:8765/verify-emoji.html
```

---

## 技術細節

### Color 變體
- **Emoji 格式**：CBDT/CBLC（NotoColorEmoji 的彩色點陣圖格式）
- **Emoji 寬度**：Runtime 偵測 Sarasa 的 half-width，emoji = 2× half-width（與 CJK 等寬）

### Lite 變體
- **Emoji 格式**：glyf TrueType outline（Noto Emoji variable font 的預設字重）
- **檔案大小**：比 Color 變體約小 30%（無點陣圖資料）
- **渲染**：Emoji 以終端機前景色顯示（單色），完整支援 Chromium/xterm.js

### 共同
- **Emoji 範圍**：單一 codepoint（ZWJ 序列/旗幟等複雜 emoji 留待 v2）
- **工具**：純 Python + fonttools，無需 FontForge 或 FontLab
- **OTS 相容**：`recalcBBoxes=False` 保留 Sarasa 原始 glyph raw bytes，通過 OTS 9.2 驗證

---

## 授權（SIL OFL 1.1）

本字體為衍生作品，遵循 SIL Open Font License 1.1：
- ✅ 可自由使用、修改、再發行
- ✅ 可與軟體捆綁發行
- ❌ 不可單獨販售
