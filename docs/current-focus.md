# Current Focus

> 最後更新：2026-04-01

## 現在狀態

- `v2.0` sequence emoji 已發佈，三個變體都已串通：
  - Color
  - Lite
  - COLRv1
- `v1.5.3` 與 COLRv1 Chromium helper metrics 修復都已歸檔，後續不需要再重做那段排查
- Release workflow 已完成 Node.js 20 警告縮減；目前只剩 `astral-sh/setup-uv@v4`，等上游有 node24 版再升級
- `Lite` 應視為 VHS / xterm.js / fallback-sensitive 環境的主力版本
- `COLRv1` 適合作為現代 renderer 的彩色加值版，不建議取代 Lite 的錄影主線
- 已完成代表樣本：
  - `👩‍💻`
  - `👋🏻`
  - `🇺🇸`
- `verify-emoji.html` 已補上 ZWJ / 膚色 / 旗幟驗證區
- Lite verify page 已改用較穩定的 text-presentation 樣本，降低 `FE0F` 觸發彩色 fallback 的干擾

### Lite 旗幟設計（已完成）

- **所有**標準 Regional Indicator（RI）雙碼序列都套用 2-column 自訂旗面設計
  - 共享旗面模板 `poc_lite_flag_template` + 壓縮字母組件 `poc_lite_letter.*`
  - 53 個 helper glyph（共用字母 + 模板），覆蓋全部 RI-pair 旗幟
- 不再使用白名單：之前的 `lite.custom_flag_sequences` 設定已移除
- 唯一有旗幟選取控制的變體是 **COLRv1**（受 glyph budget 限制，透過 `colrv1.priority_sequences` 優先保留高頻旗幟）

## 後續主線

- `v2.x`: 評估與維護
- 範圍：
  - 追蹤 `astral-sh/setup-uv` 的 node24 版
  - 維持 Lite 旗幟可讀性與三變體一致性
  - 視需要評估第四變體：emoji + Nerd Fonts PUA

## 下次開工建議先做

1. 追蹤 `astral-sh/setup-uv` 的 node24 版，屆時更新 release workflow
2. 檢查 Lite 旗幟新設計在 `Italic / Bold / BoldItalic` 的視覺一致性
3. 視使用情境繼續調整 `colrv1.priority_sequences`
4. 視需要補更多高價值 sequence regression cases

## 暫時不要重做的事

- 不用再重新調查 `🟡` / `🟢` 的 COLRv1 bug
- 不用再重新整理 `v1.5.2` / `v1.5.3` 歷史
- 不用再把 zip / png 驗證產物納入版本控制
- 先不要把 Nerd Fonts PUA merge 插隊到 `v2.0` sequence 主線之前
- 不用再重做 `extract_emoji_sequences()` / shared metadata 的基礎設計
- 不用重建 Lite 旗幟白名單：現在已全域套用，不需要分批加入
