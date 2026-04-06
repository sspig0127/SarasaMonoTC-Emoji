---
type: history
status: archived
version: v2.2
audience: maintainer
---

# v2.2.0 Release Notes（草稿）

本次 v2.2.0 聚焦在 **COLRv1 變體的 glyph budget 擴增**，讓 `SarasaMonoTCEmojiCOLRv1` 能在既有 TrueType 限制下，塞入更多實用 emoji 與 sequence，同時保留安全緩衝，不追求不可行的全量覆蓋。

---

## 變更摘要

- COLRv1 glyph budget 上限由 **8,136 提高到 8,450**
- greedy 選取策略改為 **skip-and-continue**，不再在第一個超預算 emoji 就停止
- 新增 **10 個 priority emoji**
- 新增 **221 個 priority sequences**
- COLRv1 收錄總量由 **629 提升到 811**（540 個單碼 emoji + 271 個 sequences）

---

## COLRv1 新增 emoji 重點

這次補強的重點，不是追求全量 sequence，而是優先把日常更常見、且成本效益高的項目塞進 budget 內。

### 書本 / 文具 / 時鐘系列補強

本版新增 10 個 priority emoji：

- 書寫與測量：📏、📐、📝、📜
- 書本系列：📕、📗、📘、📙、📔
- 時鐘樣本：🕑

這些項目原本在 budget-limited 選取下容易被擠掉，v2.2.0 直接列入優先清單後，COLRv1 變體在文件、筆記、閱讀、時間表達等情境會更完整。

### Sequence 擴增

- 新增 **221 個 priority sequences**
- 總 sequence 數量由 **32 增加到 271**
- 總收錄量由 **629 增加到 811**

這批擴增主要來自兩個方向：

1. 調整 greedy 演算法，讓後段仍有機會選入低成本 emoji
2. 挑選已共享 component / geometry dependency 的低成本 sequence，優先放入 `priority_sequences`

對使用者來說，代表 COLRv1 變體現在能顯示更多 ZWJ / 變體 sequence，而不必等到未來不切實際的全量覆蓋。

---

## 技術細節

### Budget 數字

| 項目 | 數字 |
|------|------|
| TrueType `numGlyphs` 硬上限 | 65,535 |
| Sarasa 最大 style glyph 數 | 56,905 |
| 理論可用上限 | 8,630 |
| v2.1 既有 `max_new_glyphs` | 8,136 |
| v2.2 新 `max_new_glyphs` | 8,450 |
| v2.2 實際消耗 | **8,327 / 8,450** |
| 剩餘緩衝 | **123 slots** |

### 選取策略調整

過去 COLRv1 greedy fill 在遇到第一個超預算 emoji 時就會直接停止，因此後面即使有 cost=1 的便宜候選，也完全沒有機會被選入。

v2.2 改為 **skip-and-continue greedy**：

- 單一候選超預算時先跳過
- 繼續往後尋找更便宜的候選
- 只在剩餘 budget 已不足，或後續候選明顯不可能再塞入時才停止

這個改法讓有限 budget 能更有效率地換到實際可見的 emoji 覆蓋提升。

### 為什麼不是全量 sequence

原因很單純：**做不到**。

- 全量 COLRv1 sequence 需求約 **18,000+ slots**
- 目前在 TrueType `numGlyphs` 限制下，實際可用空間約 **8,630**

因此 v2.2 的方向是：

- 提高 budget 上限
- 優化 greedy 演算法
- 優先加入低成本、高價值的 sequence

而不是投入大量成本追求無法達成的全量覆蓋。

---

## 補充

- 這次也同步補上 COLRv1 budget 評估文件，整理可行與不可行方向
- 詳細評估可參考：[`docs/colrv1-budget-expansion-eval.md`](./colrv1-budget-expansion-eval.md)
