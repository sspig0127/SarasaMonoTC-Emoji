# COLRv1 Sequence 擴增可行性評估

> 評估日期：2026-04-04
> 背景：技術債「COLRv1 sequence 仍為 budget-limited」的可行性分析
> 模擬分析腳本 → [`scripts/colrv1_budget_analysis.py`](../scripts/colrv1_budget_analysis.py)
> 執行：`uv run python scripts/colrv1_budget_analysis.py`（需先 `uv run python build.py --colrv1 --styles Regular` 建構字體供 HTML 顯示）

---

## 現狀預算快照

| 項目 | 數字 | 說明 |
|------|------|------|
| TrueType 硬上限 | 65,535 | numGlyphs uint16，無法突破 |
| Sarasa 字形數 | 56,886–56,905 | Regular/Bold: 56,886；Italic/BoldItalic: 56,905 |
| 理論可用 | 8,630 | 65,535 − 56,905（以最大 style 計） |
| `max_new_glyphs` | 8,450 | 2026-04-05 擴增（安全邊際 180 slots） |
| 目前實際消耗 | **8,327 / 8,450** | 單碼 7,328 + sequence 999 = **剩餘 123 slots** |
| 全量 COLRv1 需求 | ~18,000+ | 完全不可行 |

**結論**：方向一、二、三已於 2026-04-05 全部實作完成。現行預算 8,327/8,450，剩餘 123 slots 緩衝。

---

## 可行方向

### 方向一：skip-and-continue greedy（中工作量，高回報）

**現況問題**：`_select_colrv1_emoji_greedy` Phase 2 在第一個超預算 emoji 即停止（`break`），
跳過後面可能成本較低的 emoji。

**改法**：stop → skip，加上最小 cost 截止條件避免無效掃描：

```python
# src/emoji_merge.py — Phase 2 greedy fill
min_remaining = max_new_glyphs - total_cost
if min_remaining <= 0:
    break
if not _select_one(cp, is_priority=False):
    if cost > min_remaining:  # 此 emoji 獨自就超預算，後面更貴，停止
        break
    continue  # 跳過此 emoji，繼續找更便宜的
```

**前提**：需先提高 `max_new_glyphs`（方向三）；現行預算已用盡，無空間供 skip 運作。

**模擬結果（2026-04-05，+314 slots 前提）**：
- 可新增 **16 個單碼 emoji**，消耗 314/314 extra slots
- 成本分布：cost=1×5 個，其餘（cost 12–109）各 1 個
- 相比「stop at first」，skip-and-continue 在相同 extra budget 內多選入那 5 個 cost=1 的 emoji

**風險**：greedy 結果不再純粹 codepoint 升序，`colrv1-emoji-list.json` 排序改變；
需更新相關 test assertion。

視覺報表 → `scripts/colrv1_budget_report.html`（執行腳本後產生）

---

### 方向二：低成本 sequence 候選擴增（低工作量）

**關鍵洞察**：若 sequence 的所有 component 基礎 emoji 都已被 greedy 選入，
則 sequence 只需 1 個 glyph slot（composed glyph 本身共享 geometry deps）。

例如：
- 若 👩 U+1F469 和 💻 U+1F4BB 都已選入 → 👩‍💻 可能只需 cost = 1
- 若 👋 U+1F44B 已選入 → 各膚色變體 👋🏻~👋🏿 每個可能也只需 cost = 1

**模擬結果（2026-04-05）**：
- COLRv1 GSUB sequences 共 2,554 筆（旗幟已排除）
- component 都已選入的候選：**754 筆**
- 其中 cost=1（無新 dep）：**220 筆**
- 若 extra budget = 314（配合方向三），最多可加入 **309 個 cost=1 sequence**（314 − 5 slots 給方向一的 cost=1 emoji）

**行動**：從 754 筆候選中挑選高價值者加入 `config.yaml` 的 `priority_sequences`。
視覺報表 → `scripts/colrv1_budget_report.html`

---

### 方向三：小幅提高 `max_new_glyphs`（已量測）

**量測結果（2026-04-05）**：

| Style | Glyph 數 |
|-------|---------|
| Regular | 56,886 |
| Bold | 56,886 |
| Italic | 56,905 |
| BoldItalic | 56,905 |

最大值為 56,905（Italic / BoldItalic），因此：
- 理論可用上限：65,535 − 56,905 = **8,630** slots
- 現行 `max_new_glyphs: 8,136`，安全邊際 **494 slots**
- 建議提高至 **8,450**（保留 180 slot 緩衝），可額外釋放 ~314 slots

單獨執行此項變更即可立即生效，不需修改程式邏輯。

---

## 不可行方向

| 方向 | 為何不可行 |
|------|-----------|
| 改用 OTF/CFF 格式 | `numGlyphs` uint16 是 OpenType spec 層級限制，與輪廓格式無關 |
| Subsetting Sarasa | 移除 CJK 字形會破壞字體用途 |
| 全量 sequence 覆蓋 | 需 ~18,000+ slots，超出可用空間 2 倍以上 |
| 拆成兩個字體 | 需 font fallback，脫離「單一字體」設計目標 |

---

## 建議實作順序

1. ✅ 量測各 style 字形數 → 最大 56,905，可用上限 8,630，建議設 8,450
2. ✅ 模擬分析完成（`scripts/colrv1_budget_analysis.py`）→ 方向一+314 slots 可多 16 個 emoji；方向二有 220 個 cost=1 sequence 候選
3. ✅ `max_new_glyphs` 提高至 8,450（方向三）
4. ✅ skip-and-continue greedy 實作（`src/emoji_merge.py`）
5. ✅ 新增 10 個 priority_codepoints（📏📐📝📜📕📗📘📙📔🕑）+ 221 個 priority_sequences

---
