# SarasaMonoTC-Emoji

**Sarasa Mono TC（更紗黑體繁中等寬）+ NotoColorEmoji — 嵌入式彩色 emoji**

## 下載字體

前往 [Releases](https://github.com/sspig0127/SarasaMonoTC-Emoji/releases) 下載最新版本：

| 檔案 | 說明 |
|------|------|
| `SarasaMonoTCEmoji-Regular.ttf` | 一般 |
| `SarasaMonoTCEmoji-Italic.ttf` | 斜體 |
| `SarasaMonoTCEmoji-Bold.ttf` | 粗體 |
| `SarasaMonoTCEmoji-BoldItalic.ttf` | 粗斜體 |

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

**本專案**是首個用 Python/fonttools 自動化將彩色 emoji 嵌入 Sarasa Mono TC 的方案。

---

## 字體來源與授權

| 字體 | 來源 | 授權 |
|------|------|------|
| Sarasa Mono TC | [be5invis/Sarasa-Gothic](https://github.com/be5invis/Sarasa-Gothic) | SIL OFL 1.1 |
| NotoColorEmoji | [googlefonts/noto-emoji](https://github.com/googlefonts/noto-emoji) | SIL OFL 1.1 |
| **SarasaMonoTCEmoji（本專案）** | 衍生作品 | SIL OFL 1.1 |

版權聲明：見 [LICENSE](LICENSE)

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

#### 2. NotoColorEmoji

前往 [noto-emoji releases](https://github.com/googlefonts/noto-emoji/releases) 下載：

```
NotoColorEmoji.ttf  →  放入 fonts/
```

### 建構

```bash
# 安裝依賴
uv sync

# 建構全部 4 種字重
uv run python build.py

# 或只建構 Regular（快速測試）
uv run python build.py --styles Regular
```

### 輸出

```
output/fonts/
├── SarasaMonoTCEmoji-Regular.ttf
├── SarasaMonoTCEmoji-Italic.ttf
├── SarasaMonoTCEmoji-Bold.ttf
├── SarasaMonoTCEmoji-BoldItalic.ttf
└── fonts-manifest.json
```

---

## 驗證

```bash
# 基本功能驗證
uv run python -c "
from fontTools.ttLib import TTFont
f = TTFont('output/fonts/SarasaMonoTCEmoji-Regular.ttf')
assert 'CBDT' in f and 'CBLC' in f, 'Missing color tables'
cmap = f['cmap'].getBestCmap()
for cp, name in [(0x1F600, '😀'), (0x1F525, '🔥'), (0x4E00, '一')]:
    assert cp in cmap, f'Missing U+{cp:04X} {name}'
print(f'OK — Total glyphs: {len(f.getGlyphOrder())}')
"

# 瀏覽器目視驗證（需先 build，再啟動本地 server）
uv run python -m http.server 8765
open http://localhost:8765/verify-emoji.html
```

---

## 技術細節

- **Emoji 格式**：CBDT/CBLC（NotoColorEmoji 的彩色點陣圖格式）
- **Emoji 寬度**：Runtime 偵測 Sarasa 的 half-width，emoji = 2× half-width（與 CJK 等寬）
- **Emoji 範圍**：單一 codepoint（ZWJ 序列/旗幟等複雜 emoji 留待 v2）
- **工具**：純 Python + fonttools，無需 FontForge 或 FontLab
- **OTS 相容**：`recalcBBoxes=False` 保留 Sarasa 原始 glyph raw bytes，通過 OTS 9.2 驗證

---

## 授權（SIL OFL 1.1）

本字體為衍生作品，遵循 SIL Open Font License 1.1：
- ✅ 可自由使用、修改、再發行
- ✅ 可與軟體捆綁發行
- ❌ 不可單獨販售
