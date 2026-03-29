# Copilot Instructions — SarasaMonoTC-Emoji

> 目前版本：**v1.5**（2026-03-29）

## 專案概述

**SarasaMonoTC-Emoji** 是一個 Python/fonttools 自動化字體建構工具，
將 emoji 嵌入 Sarasa Mono TC（更紗黑體繁中等寬），產出三種變體：

| 變體 | 字族名稱 | Emoji 格式 | 適用場景 |
|------|----------|------------|----------|
| **Color** | `SarasaMonoTCEmoji` | CBDT/CBLC 彩色點陣圖 | 日常終端機、編輯器 |
| **Lite** | `SarasaMonoTCEmojiLite` | glyf TrueType outline（單色） | VHS 錄影、輕量部署 |
| **COLRv1** | `SarasaMonoTCEmojiCOLRv1` | COLRv1 彩色向量 | Chrome/Chromium 終端機 |

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
├── build.py                    # 主建構入口（--colrv1 / --lite / default Color）
├── config.yaml                 # 字體設定（字族名稱、樣式、路徑、emoji 選項）
├── src/
│   ├── config.py               # 設定載入與驗證
│   ├── emoji_merge.py          # 核心：emoji 嵌入邏輯（三種變體）
│   └── utils.py                # 工具函式（名稱更新、寬度驗證）
├── fonts/                      # 來源字體（.ttf，不納入版本控制）
├── output/                     # 建構輸出（不納入版本控制）
│   ├── fonts/                  # Color 變體輸出
│   ├── fonts-lite/             # Lite 變體輸出
│   └── fonts-colrv1/           # COLRv1 變體輸出
├── docs/
│   └── colrv1-emoji-list.json  # COLRv1 greedy 選取清單（由 build.py --colrv1 自動產生）
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_emoji_merge.py
│   └── test_font_output.py
├── verify-emoji.html           # 本地瀏覽器視覺驗證工具（需 http-server port 8765）
├── ROADMAP.md                  # 版本規劃與技術決策記錄（主要協作文件）
├── PLAN-COLRv1.md              # COLRv1 原始設計文件
└── PLAN-COLRv1-greedy.md       # COLRv1 greedy 選取修改計畫（v1.4.1 實作依據）
```

---

## 常用指令

```bash
# 安裝依賴
uv sync --group dev

# 建構全部樣式
uv run python build.py             # Color
uv run python build.py --lite      # Lite
uv run python build.py --colrv1    # COLRv1

# 建構單一樣式（快速測試）
uv run python build.py --styles Regular
uv run python build.py --colrv1 --styles Regular

# 執行測試
uv run pytest tests/ -v --tb=short
uv run pytest tests/test_emoji_merge.py -v

# 瀏覽器視覺驗證（需先建構完成）
uv run python -m http.server 8765
open http://localhost:8765/verify-emoji.html
```

---

## 開發注意事項

### 通用

- **設定集中管理**：所有字體參數在 `config.yaml` 修改，程式碼不 hardcode 路徑或名稱
- **三種 merge 函式**：`merge_emoji()`（Color）、`merge_emoji_lite()`（Lite）、`merge_emoji_colrv1()`（COLRv1）位於 `src/emoji_merge.py`
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
  `colrv1.force_colrv1_codepoints`（COLRv1 變體）預設值相同（5 個 BMP codepoint）。
  **修改其中一個時，請同步修改另一個。**
- **CBLC 衝突 debug log**：`_filter_cblc_to_added_glyphs` 現在在 build log 列出被移除的
  glyph 名稱（最多 10 個範例）。若 log 顯示非工具字形（.notdef / space 以外）被移除，
  可考慮將對應 codepoint 加入 `force_color_codepoints`。

### COLRv1 特有

**TrueType 65535 glyph 上限**：Sarasa 有 ~56,886 glyphs，若加入全量 COLRv1 geometry
deps（~17,433 個）和 emoji stubs（~1,358 個）合計 ~75,677，超出硬性上限。
COLRv1 必須限制選取數量（由 `_select_colrv1_emoji_greedy` 控制）。

**`_select_colrv1_emoji_greedy` 兩階段選取**（`src/emoji_merge.py`）：
- **Phase 1 — Priority 優先**：`config.yaml` 的 `colrv1.priority_codepoints`
  清單先保證入選，不受預算截止限制（目前 27 個高頻 dev/tooling emoji：🔧🔗🚀🔒🔑🔍 等）
- **Phase 2 — Greedy 填充**：剩餘預算依 codepoint 升序選入，首個超預算者停止
- **結果**：600 emoji（27 priority + 573 greedy），glyph 成本 8,132/8,136 slots
- **選取清單**：`docs/colrv1-emoji-list.json`（每次 build 自動更新，含 priority 旗標）

**geometry deps walk 注意**：Noto-COLRv1 有兩種 paint 格式：
- `PaintGlyph（Format=10）`：直接引用 geometry glyph，`walk` 可直接取得
- `PaintColrLayers（Format=1）`：間接引用 LayerList，**必須** traverse 進 LayerList 才能找到 deps
  （Noto-COLRv1 有 3,685/3,985 個 emoji 用此格式；v1.4.1 修復前只走 Format=10，導致 92% emoji 渲染亂碼）

**可調整參數**（`config.yaml` `colrv1:` 區塊）：
- `max_new_glyphs`：greedy 預算上限（預設 8136）
- `priority_codepoints`：Phase 1 優先清單（修改後下次 build 生效）

**Priority 清單挑選標準**（3 項）：
1. GitHub README / Issues / CI 表格高頻出現
2. 不在 BMP（U+FFFF 以下）— BMP 符號 Sarasa 已有，`skip_existing` 正確跳過
3. 位於 greedy 截止點之後（~U+1F500+），greedy 無法自動選入

---

## 版本歷史摘要

| 版本 | 內容 |
|------|------|
| v1.0 | 初始 Color 變體（CBDT/CBLC） |
| v1.1 | 新增 Lite 變體（glyf 單色） |
| v1.2 | 修正 Lite emoji 尺寸（UPM 縮放） |
| v1.3 | 測試框架 + 健壯性改善（T1–T4） |
| v1.4 | COLRv1 第三變體 |
| v1.4.1 | 修復 COLRv1 網頁亂碼（PaintColrLayers LayerList walk）+ greedy emoji 選取 |
| v1.4.2 | COLRv1 priority allowlist（27 個 dev emoji 保證彩色，不受 greedy 截止限制） |
| v1.5 | BMP 符號彩色覆蓋（5 個基礎清單）；glyph_forced_rename / color_forced_rename 機制；_update_cmap BMP guard；post 3.0→2.0 升級（_color 後綴持久化）；75 tests |
| v1.5.1 | force BMP 清單擴增：5 → 15（新增 ↩⌨☀☁⚙❄❌➡⬆⬇）；Budget 8132→8091 slots（幾何 dep 共享節省） |
| v2.0 | ZWJ 序列 / 旗幟 / 膚色變體（🔮 規劃中） |

---

## Claude Code / Copilot 協作分工

本專案採用 **Claude Code**（深度除錯、架構決策）與 **GitHub Copilot**（快速編輯、文件維護）的雙 AI 協作模式。

### 適合交給 Claude Code 的任務

- **字型工程除錯**：font table 結構分析（COLR/CPAL/glyf/cmap/hmtx）、OTS 驗證失敗、瀏覽器渲染異常根因分析
- **效能 / 正確性 bug**：需讀懂多個函式上下文的根因分析（如 PaintColrLayers LayerList 未 walk、glyph 上限計算）
- **架構決策**：新增變體、glyph 預算策略、greedy 演算法設計、新 config 參數影響評估
- **跨工具驗證**：用 Playwright 截圖確認渲染、用 fonttools 直接檢查字體 binary

### 適合交給 Copilot 的任務

- 文件更新（README、ROADMAP、copilot-instructions.md）
- 版本號 bump（`config.yaml` version 欄位、font name table）
- Priority 清單調整（新增 / 移除 emoji codepoint）
- 已知框架下的測試補充
- 簡單 config 欄位新增對應的邏輯

### 交接慣例

1. **Claude Code → Copilot**：Claude 完成複雜修改後，列出「待 Copilot 跟進的事項」清單（文件更新、版本 bump 等）
2. **Copilot → Claude Code**：遇到字體渲染異常、font table 驗證失敗、或需要 Playwright 目視確認時，整理現象後交回 Claude Code
3. **共用知識庫**：`ROADMAP.md`（版本狀態）、`copilot-instructions.md`（整體上下文）、`PLAN-*.md`（特定功能設計）是兩個 AI 的共同參考文件，內容變動後一律更新

### Claude Code usage limit 考量

以下任務優先安排 Copilot，減少 Claude Code context 消耗：
- 純文件更新（README / ROADMAP / copilot-instructions.md）
- 版本號 bump
- Priority emoji 清單調整
- 已知框架下的測試新增
- `config.yaml` 小改動

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
