# Current Focus

> 最後更新：2026-04-05

## 現在狀態

- `v2.1` Nerd Lite 第四變體已發佈（四個變體：Color / Lite / COLRv1 / Nerd Lite）
- `v2.2` COLRv1 budget 擴增已完成（skip-and-continue greedy + 10 priority emoji + 221 sequences；811 總計，8,327/8,450 slots）
- `v1.5.3` 與 COLRv1 Chromium helper metrics 修復都已歸檔，後續不需要再重做那段排查
- Release workflow 已完成 Node.js 20 警告縮減；目前只剩 `astral-sh/setup-uv@v4`，等上游有 node24 版再升級
- `Lite` 應視為 VHS / xterm.js / fallback-sensitive 環境的主力版本
- `COLRv1` 適合作為現代 renderer 的彩色加值版，不建議取代 Lite 的錄影主線
- COLRv1 代表 ZWJ 測試樣本改為 `❤‍🔥`（原 `👩‍💻` 的 💻 不在 budget-limited 選單）
- `verify-emoji.html` 已補上 ZWJ / 膚色 / 旗幟驗證區
- Lite verify page 已改用較穩定的 text-presentation 樣本，降低 `FE0F` 觸發彩色 fallback 的干擾

### Lite 旗幟設計（已完成）

- **所有**標準 Regional Indicator（RI）雙碼序列都套用 2-column 自訂旗面設計
  - 共享旗面模板 `poc_lite_flag_template` + 壓縮字母組件 `poc_lite_letter.*`
  - 53 個 helper glyph（共用字母 + 模板），覆蓋全部 RI-pair 旗幟
- 不再使用白名單：之前的 `lite.custom_flag_sequences` 設定已移除
- 唯一有旗幟選取控制的變體是 **COLRv1**（受 glyph budget 限制，透過 `colrv1.priority_sequences` 優先保留高頻旗幟）

## 後續主線

- `v2.x`: Nerd Lite merge + 維護
- 範圍：
  - **Nerd Lite MVP 已完成**（feature/nerd-lite-mvp，134 tests 全過），待 PR merge 回 main
    - 折衷方案：Powerline 1 欄，其他集合 2 欄
    - 評估文件：`docs/nerd-fonts-variant-eval.md`
    - 實作計畫：`docs/nerd-lite-impl-plan.md`
  - 追蹤 `astral-sh/setup-uv` 的 node24 版
  - 維持四變體一致性

## 下次開工建議先做

1. 準備 v2.2 release（COLRv1 擴增），跑完整 build + 更新版本號
2. 追蹤 `astral-sh/setup-uv` 的 node24 版，屆時更新 release workflow
3. 補 `Italic / Bold / BoldItalic` 的 output font 自動化測試（四個變體共同技術債）
4. 視使用情境繼續調整 `colrv1.priority_sequences`（剩餘 123 slots 緩衝）
5. 評估 Emoji 17.0 / Nerd Fonts 版本更新

## 暫時不要重做的事

- 不用再重新調查 `🟡` / `🟢` 的 COLRv1 bug
- 不用再重新整理 `v1.5.2` / `v1.5.3` 歷史
- 不用再把 zip / png 驗證產物納入版本控制
- 不用再重做 `extract_emoji_sequences()` / shared metadata 的基礎設計
- 不用重建 Lite 旗幟白名單：現在已全域套用，不需要分批加入
