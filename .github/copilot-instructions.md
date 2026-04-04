# Copilot Instructions — SarasaMonoTC-Emoji

> 目前版本：**v2.2.0**（2026-04-05）
> COLRv1 深度技術細節 → [`.github/colrv1-dev-notes.md`](./colrv1-dev-notes.md)（debug 時再 Read）

## 專案概述

**SarasaMonoTC-Emoji** 是一個 Python/fonttools 自動化字體建構工具，
將 emoji 嵌入 Sarasa Mono TC（更紗黑體繁中等寬），產出四種變體：

| 變體 | 字族名稱 | Emoji 格式 | 適用場景 |
|------|----------|------------|----------|
| **Color** | `SarasaMonoTCEmoji` | CBDT/CBLC 彩色點陣圖 | 日常終端機、編輯器 |
| **Lite** | `SarasaMonoTCEmojiLite` | glyf TrueType outline（單色） | VHS 錄影、輕量部署 |
| **COLRv1** | `SarasaMonoTCEmojiCOLRv1` | COLRv1 彩色向量 | Chrome/Chromium 終端機 |
| **Nerd Lite** | `SarasaMonoTCEmojiLiteNerd` | glyf TrueType + Nerd PUA | 終端機 icon、VHS 錄影含 Nerd icon |

---

## 技術堆疊

- **語言**：Python 3.10+
- **套件管理**：[uv](https://github.com/astral-sh/uv)（`pyproject.toml` 定義依賴）
- **核心依賴**：`fonttools`、`opentype-sanitizer`、`PyYAML`
- **測試框架**：pytest（`tests/`）
- **CI/CD**：GitHub Actions（`.github/workflows/test.yml`）

---

## 專案結構

```
SarasaMonoTC-Emoji/
├── build.py                    # 主建構入口（--colrv1 / --lite / --nerd-lite / default Color）
├── config.yaml                 # 字體設定（字族名稱、樣式、路徑、emoji 選項）
├── src/
│   ├── config.py               # 設定載入與驗證
│   ├── emoji_merge.py          # 核心：emoji / Nerd PUA 嵌入邏輯（四種變體）
│   └── utils.py                # 工具函式（名稱更新、寬度驗證）
├── fonts/                      # 來源字體（.ttf，不納入版本控制）
├── output/                     # 建構輸出（不納入版本控制）
│   ├── fonts/                  # Color 變體輸出
│   ├── fonts-lite/             # Lite 變體輸出
│   ├── fonts-nerd-lite/        # Nerd Lite 變體輸出
│   └── fonts-colrv1/           # COLRv1 變體輸出
├── docs/
│   └── colrv1-emoji-list.json  # COLRv1 greedy 選取清單（由 build.py --colrv1 自動產生）
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_emoji_merge.py
│   └── test_font_output.py
└── verify-emoji.html           # 本地瀏覽器視覺驗證工具（需 http-server port 8765）
```

---

## 常用指令

```bash
uv sync --group dev                          # 安裝依賴

uv run python build.py                       # Color 變體
uv run python build.py --lite               # Lite 變體
uv run python build.py --nerd-lite          # Nerd Lite 變體
uv run python build.py --colrv1             # COLRv1 變體
uv run python build.py --colrv1 --styles Regular  # 快速單樣式測試

uv run pytest tests/ -v --tb=short          # 執行測試

uv run python -m http.server 8765           # 視覺驗證（搭配 verify-emoji.html）
```

---

## 開發注意事項

### 通用

- **設定集中管理**：所有字體參數在 `config.yaml` 修改，程式碼不 hardcode 路徑或名稱
- **四種 merge 入口**：`merge_emoji()`（Color）、`merge_emoji_lite()`（Lite）、`merge_emoji_lite_nerd()`（Nerd Lite）、`merge_emoji_colrv1()`（COLRv1）位於 `src/emoji_merge.py`
- **Emoji 寬度**：`emoji_width_multiplier: 2`，即佔 2 個半寬欄位（與 CJK 全形字等寬）
- **跳過已有字形**：`skip_existing: true`，保留 Sarasa 原有字形不覆蓋
- **int16 保護**：`_scale_glyph()` 含 int16 範圍驗證（-32768 ~ 32767），超界時 raise `ValueError`
- **平行建構**：預設 4 個 worker，失敗時自動清理 partial output
- **post table 格式注意**：Sarasa 使用 `post` format 3.0（不儲存字形名稱）。
  Reload 時 fonttools 從 cmap 反推名稱（`_makeGlyphName(cp)`），
  導致自訂後綴（如 `uni2764_color`）被替換回 `uni2764`。
  `merge_emoji` Step 9.5 在偵測到 `color_forced_rename` 時自動升級至 format 2.0，
  以持久化儲存自訂字形名稱。**修改 `merge_emoji` 重命名邏輯時請確保此升級仍被觸發。**
- **BMP 強制清單同步**：`emoji.force_color_codepoints`（Color 變體）與
  `colrv1.force_colrv1_codepoints`（COLRv1 變體）預設值相同。
  **修改其中一個時，請同步修改另一個。**
- **CBLC 衝突 debug log**：`_filter_cblc_to_added_glyphs` 在 build log 列出被移除的
  glyph 名稱（最多 10 個範例）。若 log 顯示非工具字形被移除，可考慮加入 `force_color_codepoints`。

### Lite 特有

- **旗幟全域設計**：所有標準 Regional Indicator（RI）雙碼旗幟序列，一律套用 2-column 自訂旗面設計。
  - 共享模板 `poc_lite_flag_template` + 壓縮字母組件 `poc_lite_letter.*`（共 53 個 helper glyph）
  - 無白名單控制，不需要在 `config.yaml` 維護 `custom_flag_sequences`
  - 若要加 debug / 觀察樣本，直接修改 `verify-emoji.html` 的旗幟樣本清單即可
  - 相關程式碼：`src/emoji_merge.py:_build_lite_flag_poc()`、`_is_regional_indicator_flag_sequence()`

### COLRv1 特有

詳見 [`.github/colrv1-dev-notes.md`](./colrv1-dev-notes.md)。摘要：
- greedy 預算 8,450 slots（Phase 1: force + priority codepoints；Phase 2: priority sequences；Phase 3: skip-and-continue greedy 填充）
- `_scale_colrv1_paint_coords()` 負責縮放 COLR paint tree 中的 font-unit 座標（UPM 轉換必要步驟）
- geometry helper glyph 的 `hmtx` / `vmtx` 必須保留來源字體縮放後的 metrics，不能一律寫成 `(0, 0)`；
  否則 Chromium 會把高倍率 transform emoji（如 🟡 / 🟢）裁出 Clip 範圍，只剩 tiny fragment
- 可調整參數：`max_new_glyphs`、`priority_codepoints`、`priority_sequences`、`force_colrv1_codepoints`
- `verify-emoji.html` 已有來源字體對照與「COLRv1 高風險樣本」區塊，COLRv1 改動後建議至少看一次
- `tests/test_font_output.py` 已包含單點與全域 transformed-helper regression tests；調整 merge 規則後應跑完整 COLRv1 output tests

### Nerd Lite 特有

- **來源字體**：`fonts/NerdFontsSymbolsOnly/SymbolsNerdFontMono-Regular.ttf`（Nerd Fonts Symbols Only, UPM 2048）
- **UPM 縮放**：two-pass merge；Powerline 用 `scale=500/2048`，其他集合用 `scale=1000/2048`
- **折衷方案欄寬**：Powerline（E0A0–E0D7）→ 1 欄（advance=500），其他集合 → 2 欄（advance=1000）
- **設定來源**：`config.yaml` → `nerd_lite.nerd_font`、`nerd_lite.output_dir`、`nerd_lite.icon_ranges`、`nerd_lite.single_column_ranges`
- **pipeline**：先完整跑 `merge_emoji_lite()`，再做 Nerd Fonts BMP PUA 後處理，避免複製 Lite 既有 sequence / flag 邏輯

---

## Claude Code / Copilot 協作分工

### 適合交給 Claude Code 的任務

- **字型工程除錯**：font table 結構分析（COLR/CPAL/glyf/cmap/hmtx）、OTS 驗證失敗、瀏覽器渲染異常根因分析
- **效能 / 正確性 bug**：需讀懂多個函式上下文的根因分析
- **架構決策**：新增變體、glyph 預算策略、greedy 演算法設計

### 適合交給 Copilot 的任務

- 文件更新（README、ROADMAP、copilot-instructions.md）
- 版本號 bump（`config.yaml` version 欄位）
- Priority 清單調整（新增 / 移除 emoji codepoint）
- 已知框架下的測試補充

### 交接慣例

1. **Claude Code → Copilot**：複雜修改後，列出「待 Copilot 跟進的事項」
2. **Copilot → Claude Code**：字體渲染異常、font table 驗證失敗時整理現象後交回
3. **共用知識庫**：`ROADMAP.md`、`copilot-instructions.md` 變動後一律更新

---

## 溝通偏好

- **語言**：臺灣繁體中文；英文縮寫附中文譯名
- **Commit**：只在明確要求時建立，不自動提交
- **Push**：需明確要求，不自動推送
- **程式碼**：可用英文；說明、註解使用繁體中文
- **CI 檢查**：PR 觸發 Gitleaks（機密偵測）+ Trivy（弱點掃描）+ pytest

---

## 授權

SIL Open Font License 1.1（字體來源：Sarasa Gothic、Noto Emoji、Noto Color Emoji）
