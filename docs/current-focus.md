# Current Focus

> 最後更新：2026-04-06

## 現在狀態

- `v2.3` 家庭 emoji 全人物渲染修復已發佈（Chromium TrueType composite bug 繞過，29 個字形）
- `v2.2` COLRv1 budget 擴增已完成（skip-and-continue greedy + 10 priority emoji + 221 sequences；811 總計，8,327/8,450 slots）
- `v2.1` Nerd Lite 第四變體已發佈（四個變體：Color / Lite / COLRv1 / Nerd Lite）
- Release workflow 已完成 Node.js 20 警告縮減；目前只剩 `astral-sh/setup-uv@v4`，等上游有 node24 版再升級
- `Lite` 應視為 VHS / xterm.js / fallback-sensitive 環境的主力版本
- `COLRv1` 適合作為現代 renderer 的彩色加值版，不建議取代 Lite 的錄影主線
- `verify-emoji.html` 已補上 ZWJ / 膚色 / 旗幟驗證區
- 200 tests，全通（Pure logic / Noto Emoji / Sarasa / output font 四組）

### v2.3 Chromium composite 修復細節

- **問題**：Chromium TrueType composite 解析 bug——同一 composite 中 component arg encoding 從 16-bit（|offset| > 127）切回 8-bit（|offset| ≤ 127）時，前面的 16-bit component 被靜默跳過
- **觸發**：家庭 emoji（`👨‍👩‍👧‍👦` 等）的 component X offset 為 225 / 447 / -9 / -229，-9 觸發 8-bit，前兩個人物不渲染
- **解法**：`emoji_merge.py` 尾端新增步驟，對含 |offset| > 127 的 composite 用 `Glyph.getCoordinates()` 遞迴展開為 simple glyph（29 個字形）
- **不影響**：PoC 旗幟字形（小 offset composite）保持原始 composite 結構

### Lite 旗幟設計（已完成）

- **所有**標準 Regional Indicator（RI）雙碼序列都套用 2-column 自訂旗面設計
  - 共享旗面模板 `poc_lite_flag_template` + 壓縮字母組件 `poc_lite_letter.*`
  - 53 個 helper glyph（共用字母 + 模板），覆蓋全部 RI-pair 旗幟
- 不再使用白名單：之前的 `lite.custom_flag_sequences` 設定已移除
- 唯一有旗幟選取控制的變體是 **COLRv1**（受 glyph budget 限制，透過 `colrv1.priority_sequences` 優先保留高頻旗幟）

## 後續主線

- `v2.x`: 維護、技術債清償、版本追蹤
- 範圍：
  - 追蹤 `astral-sh/setup-uv` 的 node24 版
  - 維持四變體一致性
  - 評估 Emoji 17.0 / Nerd Fonts 版本更新

## 下次開工建議先做

1. 追蹤 `astral-sh/setup-uv` 的 node24 版，屆時更新 release workflow
2. 視使用情境繼續調整 `colrv1.priority_sequences`（剩餘 123 slots 緩衝）
3. 評估 Emoji 17.0 / Nerd Fonts 版本更新

## 暫時不要重做的事

- 不用再重新調查 `🟡` / `🟢` 的 COLRv1 bug
- 不用再重新整理 `v1.5.2` / `v1.5.3` 歷史
- 不用再把 zip / png 驗證產物納入版本控制
- 不用再重做 `extract_emoji_sequences()` / shared metadata 的基礎設計
- 不用重建 Lite 旗幟白名單：現在已全域套用，不需要分批加入
- 不用再重做 Chromium composite bug 排查：已在 v2.3 透過 decomposition 修復
