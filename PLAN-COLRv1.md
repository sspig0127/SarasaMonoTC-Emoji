# COLRv1 Variant Implementation Plan

## 目標

新增 `--colrv1` 建構旗標，產生第三變體 `SarasaMonoTCEmojiCOLRv1`：
- 彩色向量 emoji（COLRv1 paint tree）
- 來源：`fonts/Noto-COLRv1.ttf`（UPM=1024，~1,460 codepoint 可達 emoji）
- 相比 Color（CBDT/CBLC）：向量可縮放、檔案更小（~15 MB 估）
- 相比 Lite（glyf）：彩色

---

## 前置資訊（探索階段已確認）

- `fonts/Noto-emoji/noto-emoji-2.051/fonts/Noto-COLRv1.ttf`（4.8 MB，UPM=1024）
- ~42 個 geometry helper glyphs（PaintGlyph Format=10 引用，名稱如 `glyph06742`）
- glyph 名稱衝突：`glyph06742` 同時存在於 Sarasa 和 COLRv1 → 需重命名 geometry deps
- 現有 codebase 無 COLR/CPAL 使用
- fontTools >= 4.47（已安裝）支援 COLRv1

---

## 實作步驟

### Step 1 — `src/emoji_merge.py`：新增三個函式

#### 1a. `_collect_colrv1_paint_glyph_deps(emoji_font, target_names) -> set[str]`

走訪 `COLR` table 的 `BaseGlyphList`，對每個在 `target_names` 中的 glyph，
遞迴找出所有 `PaintGlyph`（Format=10）節點引用的 geometry helper glyph names。

```python
def _collect_colrv1_paint_glyph_deps(emoji_font, target_names: set[str]) -> set[str]:
    colr = emoji_font["COLR"].table
    if not hasattr(colr, "BaseGlyphList") or colr.BaseGlyphList is None:
        return set()
    deps = set()
    target_set = set(target_names)

    def walk(paint):
        if paint is None:
            return
        if paint.Format == 10:  # PaintGlyph
            deps.add(paint.Glyph)
            walk(paint.Paint)
        else:
            for attr in ("Paint", "SourcePaint", "BackdropPaint"):
                child = getattr(paint, attr, None)
                if child:
                    walk(child)
            for child in getattr(paint, "Paints", []):
                walk(child)

    for record in colr.BaseGlyphList.BaseGlyphPaintRecord:
        if record.BaseGlyph in target_set:
            walk(record.Paint)
    return deps
```

#### 1b. `_filter_colr_to_added_glyphs(base_font, added_set: set[str]) -> None`

過濾已合併到 `base_font` 的 COLR table，只保留 `added_set` 中的記錄：
- `BaseGlyphList.BaseGlyphPaintRecord`（COLRv1）
- `BaseGlyphRecord`（COLRv0，保留以防萬一）
- `ClipList`（若存在）
- 更新 `BaseGlyphCount`

```python
def _filter_colr_to_added_glyphs(base_font, added_set: set[str]) -> None:
    colr = base_font["COLR"].table
    if hasattr(colr, "BaseGlyphList") and colr.BaseGlyphList:
        records = colr.BaseGlyphList.BaseGlyphPaintRecord
        colr.BaseGlyphList.BaseGlyphPaintRecord = [
            r for r in records if r.BaseGlyph in added_set
        ]
    if hasattr(colr, "BaseGlyphRecord") and colr.BaseGlyphRecord:
        colr.BaseGlyphRecord = [
            r for r in colr.BaseGlyphRecord if r.BaseGlyph in added_set
        ]
    if hasattr(colr, "ClipList") and colr.ClipList:
        colr.ClipList.clips = {
            k: v for k, v in colr.ClipList.clips.items() if k in added_set
        }
```

#### 1c. `merge_emoji_colrv1(base_font_path, emoji_font_path, config) -> TTFont`

9 步驟合併流程（與 `merge_emoji` 相同骨架）：

1. 載入兩個字體，偵測 half_w / full_w
2. 提取 emoji cmap（`get_emoji_cmap()`，過濾 ASCII、VS）
3. 跳過 base font 已有的 codepoint（`config.skip_existing`）
4. 計算 UPM 縮放比：`upm_scale = base_upm / emoji_upm`（1000/1024 ≈ 0.977）
5. 收集 geometry deps：`_collect_colrv1_paint_glyph_deps(emoji_font, target_names)`
   - **重命名衝突**：geometry dep 名稱如果與 base font 現有 glyph 衝突，加 `_colrv1` 後綴
6. 深拷貝 COLR + CPAL（`emoji_font["COLR"].table.decompile()` 先 decompile → `copy.deepcopy`）
7. **vmtx 前先存取 base glyf**（解決 OTS ordering constraint）：`base_glyf = base_font["glyf"]`
8. 設定新 glyph order：`base_font.setGlyphOrder(existing + geometry_deps_list + emoji_list)`
9. 加入 geometry dep glyphs（真實 glyf outline，套用 `_scale_glyph(upm_scale)`）
10. 加入 emoji glyphs（**空 glyf stub**，paint tree 驅動渲染）
11. 更新 hmtx/vmtx（emoji_w = half_w * multiplier；geometry deps 用 advance=0）
12. 更新 maxp.numGlyphs
13. 更新 cmap
14. 更新 hhea.numberOfHMetrics、OS/2
15. 複製 COLR + CPAL 到 base_font，呼叫 `_filter_colr_to_added_glyphs()`
16. `_strip_mac_name_records(base_font)`

### Step 2 — `build.py`：新增 `--colrv1` 旗標

```python
parser.add_argument("--colrv1", action="store_true",
    help="Build COLRv1 variant: color vector emoji (Chrome 98+, smaller files). "
         "Requires Noto-COLRv1.ttf in fonts/ directory.")
```

- 與 `--lite` 互斥：若同時指定，`sys.exit(1)` 提示錯誤
- 3-way dispatch：`is_lite` / `is_colrv1` / color（預設）
- 讀取 `colrv1:` config section（family_name、emoji_font、output_dir、description）
- `variant_label = "COLRv1 (color vector)"`
- 錯誤訊息指向正確下載連結

### Step 3 — `config.yaml`：新增 `colrv1:` 區塊

```yaml
colrv1:
  family_name: "SarasaMonoTCEmojiCOLRv1"
  emoji_font: "Noto-COLRv1.ttf"
  output_dir: "output/fonts-colrv1"
  description: "Sarasa Mono TC (更紗黑體繁中等寬) with embedded Noto COLRv1 — color vector emoji for Chrome/Chromium terminals"
```

### Step 4 — `verify-emoji.html`：新增 COLRv1 選項

- `VARIANTS` 物件加入 `colrv1: { dir: "output/fonts-colrv1", label: "COLRv1" }`
- `<select>` 加入 `<option value="colrv1">COLRv1（彩色向量）</option>`
- CSS 加入 `.badge-colrv1 { background: #673ab7; color: white; }` 紫色 badge

### Step 5 — 測試

#### `tests/conftest.py`
新增 `output_colrv1_regular` fixture（與 `output_color_regular` 同模式）

#### `tests/test_font_output.py`
新增 `TestCOLRv1Output`（10 tests）：
1. COLR table 存在
2. CPAL table 存在
3. 無 CBDT/CBLC tables
4. 關鍵 codepoint 存在（😀 U+1F600、🔥 U+1F525、一 U+4E00）
5. Emoji glyph 寬度 = 2× half_width
6. Geometry dep glyphs 已加入（驗證非空 glyf outlines）
7. Glyph 總數合理範圍
8. 無 Mac platform name records
9. family_name 含 "COLRv1"
10. COLR BaseGlyphPaintRecord 數量 > 0

#### `tests/test_emoji_merge.py`
新增 `TestFilterColrToAddedGlyphs`（3 tests）：
1. 過濾後只剩指定 glyphs
2. ClipList 同步過濾
3. 空 added_set 清空 records

---

## 檔案影響範圍

| 檔案 | 變動 |
|------|------|
| `src/emoji_merge.py` | 新增 3 個函式 |
| `build.py` | 新增 `--colrv1` flag + 3-way dispatch |
| `config.yaml` | 新增 `colrv1:` section |
| `verify-emoji.html` | COLRv1 option |
| `tests/conftest.py` | 新增 fixture |
| `tests/test_font_output.py` | 新增 TestCOLRv1Output |
| `tests/test_emoji_merge.py` | 新增 TestFilterColrToAddedGlyphs |
| `ROADMAP.md` | 更新 v2.x COLRv1 狀態 |

---

## 注意事項

1. **vmtx ordering**：`maxp.numGlyphs` 必須在 vmtx 存取後才更新
2. **geometry dep 命名衝突**：`glyph06742` 需重命名，COLR paint tree 引用名稱也需同步更新
3. **深拷貝前 decompile**：`COLR` 必須先 `table.decompile()` 再 `copy.deepcopy()`，否則懶載入物件無法正確複製
4. **emoji stub glyph**：COLRv1 emoji 的 glyf 可以是空（zero contour），paint tree 提供所有渲染資訊
