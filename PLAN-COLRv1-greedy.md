# COLRv1 Greedy Emoji 選取修改計畫

## 問題描述

COLRv1 變體在網頁版測試顯示亂碼，根因是加入了過多 glyph，
超出瀏覽器 / OTS 可正常處理的上限。

## 解決方向

限制 COLRv1 新增 glyph 總數（含 geometry deps）在 **8,136** 以內，
方法：按 codepoint 升序 greedy 選取約 600 個常用 emoji（舊 codepoint 排在前面，相對常用）。

---

## 目前程式流程（merge_emoji_colrv1）

```
載入字體
→ get_emoji_cmap()                           # 全量 ~1,400+ codepoints
→ 過濾 base font 已有 codepoints
→ _collect_colrv1_paint_glyph_deps()         # 算 geometry deps
→ 重命名衝突 geometry deps
→ 設定 glyph order、複製 glyf、hmtx、COLR/CPAL
→ 回傳 TTFont
```

**新增步驟**：在「過濾已有 codepoints」之後、「收集 geometry deps」之前，
插入 greedy 選取邏輯。

---

## 修改計畫

### 1. `src/emoji_merge.py`

#### 新增函式：`_select_colrv1_emoji_greedy`

**位置**：放在 `_collect_colrv1_paint_glyph_deps` 之前

**簽名**：
```python
def _select_colrv1_emoji_greedy(
    emoji_cmap: dict[int, str],
    emoji_font: TTFont,
    max_new_glyphs: int,
) -> tuple[dict[int, str], list[dict]]:
```

**演算法**：
1. 按 codepoint 升序排列
2. 對每個 emoji，呼叫 `_collect_colrv1_paint_glyph_deps(emoji_font, {glyph_name})` 取得其 geometry deps
3. 計算此 emoji 的「新增成本」= 1（emoji stub）+ 尚未被前面 emoji 佔用的 dep 數量
4. 若累計 `total + cost <= max_new_glyphs`：選入，更新累計集合
5. 若超出：**break**（不繼續嘗試後續 emoji，確保決定論、可重現）
6. 回傳 `(filtered_cmap, selection_records)`

**`selection_records` 元素格式**：
```python
{
  "codepoint": "U+1F600",
  "char": "😀",
  "glyph_name": "u1F600",
  "unicode_name": "GRINNING FACE",    # unicodedata.name(chr(cp), "UNKNOWN")
  "geometry_deps_count": 5,           # 此 emoji 引用的 dep 總數（含共用）
  "new_glyph_cost": 3,                # 實際新增 glyph 數（扣除已計入的共用 dep）
}
```

#### 修改函式：`merge_emoji_colrv1`

**簽名新增參數**：
```python
def merge_emoji_colrv1(
    base_font_path: str,
    emoji_font_path: str,
    config: FontConfig,
    max_new_glyphs: int | None = None,   # 新增
) -> tuple[TTFont, list[dict]]:          # 回傳型別改為 tuple
```

**插入位置**（步驟 3.5，濾除已有 codepoints 之後）：
```python
# Step 3.5: greedy 選取（COLRv1 glyph 預算控制）
selection_records: list[dict] = []
if max_new_glyphs is not None:
    emoji_cmap, selection_records = _select_colrv1_emoji_greedy(
        emoji_cmap, emoji_font, max_new_glyphs
    )
    print(f"  Greedy selection: {len(emoji_cmap)} emoji selected "
          f"(budget: {max_new_glyphs} new glyphs)")
```

**回傳**：`return base_font, selection_records`（尾端改為 tuple）

> ⚠️ 回傳型別從 `TTFont` 改為 `tuple[TTFont, list[dict]]`，
> 只影響一個呼叫端：`build.py` 的 `build_single_font`。

---

### 2. `build.py`

#### `build_single_font` 修改

**新增參數**：
```python
def build_single_font(
    ...,
    max_new_glyphs: int | None = None,   # 新增
) -> tuple[str, list[dict]]:             # 回傳改為 (path, selection_records)
```

**COLRv1 dispatch 修改**：
```python
elif colrv1:
    merged_font, selection_records = merge_emoji_colrv1(
        base_font_path=str(base_font_path),
        emoji_font_path=str(emoji_font_path),
        config=config,
        max_new_glyphs=max_new_glyphs,
    )
```

非 COLRv1 branch：`selection_records = []`

**回傳**：`return str(output_path), selection_records`

#### `main()` 修改

1. 讀取 config：
   ```python
   max_new_glyphs = get_config_int(yaml_config, "colrv1", "max_new_glyphs", default=8136)
   emoji_list_path = get_config_value(yaml_config, "colrv1", "emoji_list_path") \
       or "docs/colrv1-emoji-list.json"
   ```

2. COLRv1 parallel 建構後，取 Regular style 的 `selection_records` 寫入 JSON：
   ```python
   if is_colrv1 and selection_records:
       _write_emoji_list(
           records=selection_records,
           output_path=Path(emoji_list_path),
           version=config.version,
           max_new_glyphs=max_new_glyphs,
       )
   ```

3. 新增輔助函式 `_write_emoji_list`：
   ```python
   def _write_emoji_list(records, output_path, version, max_new_glyphs):
       output_path.parent.mkdir(parents=True, exist_ok=True)
       data = {
           "generated": datetime.now(timezone.utc).isoformat(),
           "version": version,
           "max_new_glyphs": max_new_glyphs,
           "selected_count": len(records),
           "total_glyph_cost": sum(r["new_glyph_cost"] for r in records),
           "emoji": records,
       }
       output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
       print(f"  Emoji list written: {output_path} ({len(records)} emoji)")
   ```

> **Parallel 建構注意**：`build_single_font` 在 `ProcessPoolExecutor` 中執行，
> 回傳值需透過 futures 收集。需更新 `as_completed` 迴圈以收取 `(path, records)` tuple。
> 只取其中一個 style（Regular 或第一個完成的）的 `selection_records` 即可，
> 因為所有 style 使用相同 emoji font，選取結果一致。

---

### 3. `config.yaml`

在 `colrv1:` 區塊新增兩個欄位：

```yaml
colrv1:
  family_name: "SarasaMonoTCEmojiCOLRv1"
  emoji_font: "Noto-COLRv1.ttf"
  output_dir: "output/fonts-colrv1"
  description: "..."
  # 新增：
  max_new_glyphs: 8136    # 限制新增 glyph 總數（含 geometry deps），解決網頁亂碼問題
  emoji_list_path: "docs/colrv1-emoji-list.json"  # 選取清單輸出路徑（納入版本控制）
```

---

## 新增輸出檔案

**`docs/colrv1-emoji-list.json`**（build 產出、納入版本控制）

```json
{
  "generated": "2025-01-01T00:00:00+00:00",
  "version": "1.4",
  "max_new_glyphs": 8136,
  "selected_count": 612,
  "total_glyph_cost": 8130,
  "emoji": [
    {
      "codepoint": "U+0023",
      "char": "#",
      "glyph_name": "uni0023",
      "unicode_name": "NUMBER SIGN",
      "geometry_deps_count": 4,
      "new_glyph_cost": 5
    },
    ...
  ]
}
```

不需加入 `.gitignore`（`docs/` 目錄未被排除，應納入版控）。

---

## 測試計畫

### `tests/test_emoji_merge.py`：新增 `TestSelectColrv1EmojiGreedy`

需要 `requires_noto_colrv1` marker（Noto-COLRv1.ttf，非 CI 環境）：

1. 在預算充足時全選
2. 超出預算時在正確數量截止
3. selection_records 欄位完整（codepoint、char、glyph_name、unicode_name、new_glyph_cost）
4. 總 glyph cost ≤ max_new_glyphs
5. codepoint 順序保持升序

> CI 中不需要此測試通過（Noto-COLRv1.ttf 不在 CI 下載清單），
> 使用 `pytest.mark.skipif` 處理。

---

## 影響範圍總覽

| 檔案 | 變動性質 |
|------|---------|
| `src/emoji_merge.py` | 新增 `_select_colrv1_emoji_greedy`；修改 `merge_emoji_colrv1` 簽名與回傳型別 |
| `build.py` | 修改 `build_single_font` 簽名與回傳型別；`main()` 讀取新 config 欄位、寫入 JSON |
| `config.yaml` | `colrv1:` 新增 `max_new_glyphs`、`emoji_list_path` |
| `docs/colrv1-emoji-list.json` | 新建目錄與檔案（build 產出） |
| `tests/test_emoji_merge.py` | 新增 `TestSelectColrv1EmojiGreedy`（選做） |

**不影響**：Color 變體、Lite 變體、現有測試、CI workflow

---

## 技術注意事項

1. **Break vs continue**：greedy 算法在第一個超出預算的 emoji 時 break（非 skip），確保選取結果的決定論性
2. **Geometry dep 共用計算**：`accumulated_deps` 集合跨 emoji 維護，正確計算共用 dep 的「邊際成本」
3. **`_collect_colrv1_paint_glyph_deps` 效能**：每個 emoji 各呼叫一次，約 600 次走訪 COLR paint tree，實測可接受（非 CI 瓶頸）
4. **Parallel futures 收集**：`ProcessPoolExecutor` 回傳 tuple，`as_completed` 迴圈需調整解包邏輯
5. **`datetime` import**：`build.py` 新增 `from datetime import datetime, timezone`
