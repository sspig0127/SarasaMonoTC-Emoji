# Current Focus

> 最後更新：2026-03-31

## 現在狀態

- `v1.5.3` 已完成並發佈
- COLRv1 Chromium helper metrics bug 已修復
- `v2.0` sequence emoji MVP 已串通三個變體：
  - Color
  - Lite
  - COLRv1
- `Lite` 應視為 VHS / xterm.js / fallback-sensitive 環境的主力版本
- `COLRv1` 適合作為現代 renderer 的彩色加值版，不建議取代 Lite 的錄影主線
- 已完成代表樣本：
  - `👩‍💻`
  - `👋🏻`
  - `🇺🇸`
- `verify-emoji.html` 已補上 ZWJ / 膚色 / 旗幟驗證區
- Lite verify page 已改用較穩定的 text-presentation 樣本，降低 `FE0F` 觸發彩色 fallback 的干擾
- Lite 六個高頻旗幟（`TW / JP / US / CN / GB / CA`）已開始做可讀性微調
- Lite 旗幟縮寫在 2-column 限制下仍有可讀性上限；目前先記錄為已知限制，暫不再做高風險 flag redraw

## 下個版本主線

- `v2.0`: 支援 sequence emoji
- 範圍：
  - ZWJ
  - 膚色變體
  - 旗幟
- `v2.x` 可評估新增第四變體：emoji + Nerd Fonts PUA

## 下次開工建議先做

1. 檢查 Lite 旗幟微調在 `Italic / Bold / BoldItalic` 的視覺一致性
2. 規劃 `v2.0` release note 與發佈條件
3. 視使用情境繼續調整 `colrv1.priority_sequences`
4. 視需要補更多高價值 sequence regression cases

## 暫時不要重做的事

- 不用再重新調查 `🟡` / `🟢` 的 COLRv1 bug
- 不用再重新整理 `v1.5.2` / `v1.5.3` 歷史
- 不用再把 zip / png 驗證產物納入版本控制
- 先不要把 Nerd Fonts PUA merge 插隊到 `v2.0` sequence 主線之前
- 不用再重做 `extract_emoji_sequences()` / shared metadata 的基礎設計
