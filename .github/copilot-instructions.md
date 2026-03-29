# Copilot Instructions — SarasaMonoTC-Emoji

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
├── build.py              # 主建構入口
├── config.yaml           # 字體設定（字族名稱、樣式、路徑、emoji 選項）
├── src/
│   ├── config.py         # 設定載入與驗證
│   ├── emoji_merge.py    # 核心：emoji 嵌入邏輯（三種變體）
│   └── utils.py          # 工具函式（名稱更新、寬度驗證）
├── fonts/                # 來源字體（.ttf，不納入版本控制）
├── output/               # 建構輸出（不納入版本控制）
│   ├── fonts/            # Color 變體輸出
│   ├── fonts-lite/       # Lite 變體輸出
│   └── fonts-colrv1/     # COLRv1 變體輸出
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_emoji_merge.py
│   └── test_font_output.py
└── verify-emoji.html     # 本地瀏覽器視覺驗證工具
```

---

## 常用指令

```bash
# 安裝依賴
uv sync --group dev

# 建構全部樣式（Color 變體）
uv run python build.py

# 建構指定樣式
uv run python build.py --styles Regular
uv run python build.py --styles Regular,Bold --parallel 2

# 執行測試
uv run pytest tests/ -v --tb=short

# 執行特定測試檔
uv run pytest tests/test_emoji_merge.py -v
```

---

## 開發注意事項

- **設定集中管理**：所有字體參數（字族名稱、樣式、路徑、emoji 寬度倍率等）在 `config.yaml` 修改
- **三種 merge 函式**：`merge_emoji()`（Color）、`merge_emoji_lite()`（Lite）、`merge_emoji_colrv1()`（COLRv1）位於 `src/emoji_merge.py`
- **Emoji 寬度**：`emoji_width_multiplier: 2`，即佔 2 個半寬欄位（與 CJK 全形字等寬）
- **跳過已有字形**：`skip_existing: true`，保留 Sarasa 原有字形不覆蓋
- **int16 保護**：`_scale_glyph()` 含 int16 範圍驗證（-32768 ~ 32767），超界時 raise `ValueError`
- **平行建構**：預設 4 個 worker，失敗時自動清理 partial output

---

## 版本歷史摘要

| 版本 | 內容 |
|------|------|
| v1.0 | 初始 Color 變體（CBDT/CBLC） |
| v1.1 | 新增 Lite 變體（glyf 單色） |
| v1.2 | 修正 Lite emoji 尺寸（UPM 縮放） |
| v1.3 | 測試框架 + 健壯性改善 |
| v1.4 | COLRv1 第三變體 |
| v2.0 | ZWJ 序列 / 旗幟 / 膚色變體（🔮 規劃中） |

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
