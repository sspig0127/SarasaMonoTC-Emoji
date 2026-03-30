# SarasaMonoTC-Emoji — Claude Code Context

Python/fonttools 自動化字體建構工具，將 emoji 嵌入 Sarasa Mono TC，產出 3 種變體：

- `Color`: CBDT/CBLC 彩色點陣圖
- `Lite`: glyf 單色 outline
- `COLRv1`: 彩色向量 paint tree

## 先讀哪些檔

### 必讀

| 檔案 | 用途 |
|------|------|
| `build.py` | 主建構入口；`--lite` / `--colrv1` / 預設 Color |
| `config.yaml` | 單一設定來源；字族名稱、輸出路徑、priority/force 清單都在這裡 |
| `src/emoji_merge.py` | 核心 merge 邏輯；三種變體都在這裡實作 |
| `src/config.py` | `FontConfig` 驗證 |
| `tests/test_emoji_merge.py` | 核心 pure logic / COLRv1 相關測試 |
| `tests/test_font_output.py` | 建構輸出驗證 |

### 需要時再讀

| 檔案 | 何時讀 |
|------|--------|
| `.github/copilot-instructions.md` | 需要完整專案規範、CI/CD、長版分工說明時 |
| `.github/colrv1-dev-notes.md` | debug COLRv1 渲染、glyph budget、UPM 縮放時 |
| `ROADMAP.md` | 確認版本狀態、正在進行的修復 |
| `docs/roadmap-history.md` | 需要查 v1.3–v1.5 細節時 |
| `verify-emoji.html` | 本地瀏覽器視覺驗證 |

## 專案結構

```text
build.py
config.yaml
src/
  config.py
  emoji_merge.py
  utils.py
tests/
docs/
verify-emoji.html
fonts/               # 來源字體，不納入版本控制
output/              # 建構輸出，不納入版本控制
```

## 常用指令

```bash
uv sync --group dev

uv run python build.py
uv run python build.py --lite
uv run python build.py --colrv1

uv run python build.py --styles Regular
uv run python build.py --colrv1 --styles Regular

uv run pytest tests/ -v --tb=short
uv run python -m http.server 8765
```

驗證頁：

- `http://localhost:8765/verify-emoji.html`
- `verify-emoji.html` 已加入 font URL cache-busting；重 build 後重新整理頁面應載入最新字體，不該再吃舊 cache

## Source Of Truth

- 所有字體名稱、版本、輸出路徑、priority 清單、force 清單，只改 `config.yaml`
- 不要在 Python 程式碼 hardcode family name、output dir、codepoint 清單
- `docs/colrv1-emoji-list.json` 是 `build.py --colrv1` 產物，不手改

## 關鍵規則

### 通用

- `emoji_width_multiplier` 預設 `2`，emoji 必須維持 2 columns
- `skip_existing: true` 預設保留 Sarasa 原有字形，不隨意覆蓋
- 不自動 commit、不自動 push，只有在明確要求時才做
- 說明與文件偏好使用繁體中文；程式碼可用英文

### Color / COLRv1 一致性

- `emoji.force_color_codepoints` 與 `colrv1.force_colrv1_codepoints` 預設應保持同步
- 若修改其中一份 BMP 強制彩色清單，另一份也要同步修改

### Name Table / Post Table

- `update_font_names()` 後要再次 `_strip_mac_name_records()`，避免 Mac platform name records 回流
- Color 變體若啟用 forced BMP rename（如 `uni2764_color`），必須維持 `post` format 2.0；否則 save/reload 後 glyph name 會丟失

### Build 穩定性

- 平行建構失敗時要清 partial output，避免輸出目錄混新舊字體
- `detect_font_widths()` 依賴字體實際寬度偵測，不要重新硬編碼 500/1000 假設

## COLRv1 Debug 重點

### 目前已知背景

- Noto-COLRv1 `UPM=1024`，Sarasa `UPM=1000`
- COLRv1 不只要縮放 glyf geometry，也要同步縮放 paint tree 中的 font-unit 座標
- `PaintGlyph` 使用到的 geometry helper glyph metrics 也要保留來源字體縮放後的值，不能直接清成 `(0, 0)`
- `🟡` / `🟢` 這類大位移 transform emoji，是驗證 UPM 縮放是否正確的高風險樣本

### 先看哪裡

- `src/emoji_merge.py:_select_colrv1_emoji_greedy`
- `src/emoji_merge.py:_collect_colrv1_paint_glyph_deps`
- `src/emoji_merge.py:_scale_colrv1_paint_coords`
- `src/emoji_merge.py:merge_emoji_colrv1`
- `.github/colrv1-dev-notes.md`

### 常見症狀對照

- emoji 完全缺失：先查 greedy selection 是否入選、`docs/colrv1-emoji-list.json` 是否存在該 codepoint
- emoji 只剩碎片或 tiny shape：優先懷疑 paint tree 座標沒跟著 UPM 縮放
- emoji 來源字體正常、合併後異常：再查 helper glyph metrics 是否被清成 `(0, 0)`
- 瀏覽器頁面看起來仍是舊 bug：先排除 `verify-emoji.html` 或瀏覽器 font cache
- 網頁亂碼或大量缺字：先檢查 glyph budget / greedy cutoff / OTS 行為

### 這次修補的關鍵概念

- `_scale_glyph()` 處理 geometry dep 的輪廓縮放
- `_scale_colrv1_paint_coords()` 處理 COLR paint tree 的 `dx/dy`、gradient control points、`centerX/centerY`、`ClipList`
- `merge_emoji_colrv1()` 會保留 geometry helper glyph 的縮放後 metrics；這是 Chromium 正確渲染高倍率 transform emoji 的必要條件
- 只縮放 font-unit 值；不要動 scale ratio、rotation angle 這類 unitless 值

## 工作流程建議

1. 先看 `git status`
2. 讀 `CLAUDE.md` + `config.yaml` + 相關核心檔
3. 若是 COLRv1 問題，再補讀 `.github/colrv1-dev-notes.md`
4. 改完先跑最小必要測試
5. 若是渲染問題，再用 `verify-emoji.html` 做視覺確認
6. COLRv1 改動後，至少看一次第 5 區來源字體對照與第 6 區高風險樣本
7. COLRv1 merge 規則調整後，至少跑 `tests/test_font_output.py -k COLRv1`
8. 若更新版本或行為，補 `ROADMAP.md` / 相關文件

## 修改前自我檢查

- 這次改動有沒有破壞三種變體之一？
- 有沒有把設定寫死到程式碼？
- 有沒有忘記同步 BMP force 清單？
- 有沒有讓字寬不再是 2 columns？
- 有沒有只修 code，卻沒更新測試或驗證頁案例？
