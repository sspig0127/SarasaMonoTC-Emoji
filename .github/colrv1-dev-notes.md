# COLRv1 變體開發細節

> 從 `copilot-instructions.md` 分離（2026-03-30）。
> 僅在 debug COLRv1 建構或渲染問題時才需要 Read 此檔案。

---

## TrueType 65535 glyph 上限

Sarasa 有 ~56,886 glyphs，若加入全量 COLRv1 geometry
deps（~17,433 個）和 emoji stubs（~1,358 個）合計 ~75,677，超出硬性上限。
COLRv1 必須限制選取數量（由 `_select_colrv1_emoji_greedy` 控制）。

## `_select_colrv1_emoji_greedy` 兩階段選取（`src/emoji_merge.py`）

- **Phase 1 — Priority 優先**：`config.yaml` 的 `colrv1.priority_codepoints`
  清單先保證入選，不受預算截止限制（目前 52 個高頻 dev/tooling emoji：🔧🔗🚀🔒🔑🔍📏📐📝📜📕📗📘📙📔🕑 等）
- **Phase 2 — Greedy 填充**：剩餘預算依 codepoint 升序選入，超預算者 skip 繼續掃描
  （v2.2 起改為 skip-and-continue，非首個超預算即停止）
- **結果**：540 單碼 emoji（52 priority + 488 greedy）+ 271 sequences，
  單碼成本 7,328 + sequence 999 = **8,327/8,450 slots（剩餘 123）**
- **選取清單**：`docs/colrv1-emoji-list.json`（每次 build 自動更新，含 priority 旗標）

## geometry deps walk 注意

Noto-COLRv1 有兩種主要 paint 格式：
- `PaintGlyph（Format=10）`：直接引用 geometry glyph
- `PaintColrLayers（Format=1）`：間接引用 LayerList，**必須** traverse 進 LayerList 才能找到 deps
  （Noto-COLRv1 有 3,685/3,985 個 emoji 用此格式；v1.4.1 修復前只走 Format=10，導致 92% emoji 渲染亂碼）

## UPM 縮放注意（v1.5.2 修復）

Noto-COLRv1 UPM=1024，Sarasa UPM=1000。合併時：
- `_scale_glyph()` 縮放幾何 dep 輪廓（×0.9766）
- `_scale_colrv1_paint_coords()` **必須同步縮放** COLR paint tree 中的 font-unit 座標：
  - `PaintTransform`（Format=12）的 `Transform.dx / .dy`（F16Dot16 float）
  - `PaintTranslate`（Format=14）的 `dx / dy`（FWORD int16，需 otRound）
  - `PaintLinearGradient`（Format=4）的 `x0,y0,x1,y1,x2,y2`（FWORD，需 otRound）
  - `PaintRadialGradient`（Format=6）的 `x0,y0,r0,x1,y1,r1`（FWORD，需 otRound）
  - `PaintSweepGradient`（Format=8）的 `centerX / centerY`（FWORD，需 otRound）
  - 任何含 `centerX / centerY` 屬性的格式（scale/rotate/skew 變體）
  - `ClipList` 的 `xMin/yMin/xMax/yMax`（otRound）
- **不縮放**：unitless 值（scale ratio、rotation angle）

**症狀**：未縮放時，大 dx 平移的 emoji（如 🟡U+1F7E1）渲染邊界落於 ClipBox 之外，
PaintTransform 層完全不渲染，只剩 Layer 3 tiny shape（9×9px）。🔴🔵 因 dx≈0 不受影響。

## helper glyph metrics 注意（v1.5.2 根因）

除了 paint tree 座標之外，`PaintGlyph` 引用的 geometry helper glyph metrics 也不能隨意丟掉。

- 來源 Noto-COLRv1 的 helper glyph 在 `hmtx` / `vmtx` 通常有非零 metrics
- merge 後若把這些 helper glyph 一律寫成 `(0, 0)`，Chromium 的 COLRv1 渲染會把高倍率 transform
  emoji 推離預期位置
- 實際症狀和未縮放 `Transform.dx/dy` 很像：🟡 / 🟢 只剩 tiny fragment，看起來像被 ClipBox 裁掉
- 目前 `merge_emoji_colrv1()` 會保留來源字體縮放後的 helper metrics；修改這段時不要退回「internal glyph 所以 metrics 全設 0」的做法

## 驗證方式（v1.5.3 補強）

- `verify-emoji.html`
  - 第 5 區：合併後字體 vs 原始來源字體
  - 第 6 區：COLRv1 高風險樣本（大量 `PaintTransform -> PaintGlyph` 案例）
- `tests/test_font_output.py`
  - `test_transformed_helper_glyph_metrics_preserved`
  - `test_all_transformed_helper_glyph_metrics_preserved`

若來源字體正常、合併後字體異常，優先檢查：

1. `_scale_colrv1_paint_coords()` 是否漏縮放某種 paint node
2. geometry helper glyph 的 `hmtx` / `vmtx` 是否被清成 `(0, 0)`
3. rename 後的 `PaintGlyph.Glyph` 是否仍指向正確 helper glyph

## Sarasa 幾何 dep 名稱衝突

Sarasa post format 3.0 有 ~6,255 個 auto-named glyph（`glyph05035` 格式，
zero-padded 5 位數），與 Noto geometry dep 名稱衝突時自動 rename 為 `xxx_colrv1`。
build log 顯示 "Renaming N conflicting geometry dep(s)"（目前約 3,138 個）。

## 可調整參數（`config.yaml` `colrv1:` 區塊）

- `max_new_glyphs`：greedy 預算上限（現行 8,450；安全邊際 180 slots；見 `docs/colrv1-budget-expansion-eval.md`）
- `priority_codepoints`：Phase 1 優先清單（修改後下次 build 生效）
- `priority_sequences`：優先 sequence 清單；pre-reserve 成本（目前估算 1,122 slots，實際消耗 999）從 `max_new_glyphs` 扣除
  - 注意：`_estimate_colrv1_priority_sequence_cost` 會高估（未計算 single-emoji 已累積的 dep），
    實際剩餘序列 budget 通常比預估多
- `force_colrv1_codepoints`：BMP 符號強制彩色覆蓋清單（與 `emoji.force_color_codepoints` 保持同步）

## Priority 清單挑選標準（3 項）

1. GitHub README / Issues / CI 表格高頻出現
2. 不在 BMP（U+FFFF 以下）— BMP 符號 Sarasa 已有，`skip_existing` 正確跳過
3. 位於 greedy 截止點之後（~U+1F500+），greedy 無法自動選入
