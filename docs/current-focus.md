# Current Focus

> 最後更新：2026-03-31

## 現在狀態

- `v1.5.3` 已完成並發佈
- COLRv1 Chromium helper metrics bug 已修復
- 文件已補齊到可準備開始 `v2.0`

## 下個版本主線

- `v2.0`: 支援 sequence emoji
- 範圍：
  - ZWJ
  - 膚色變體
  - 旗幟

## 下次開工建議先做

1. 讀 `docs/v2-sequence-implementation.md`
2. 在 `src/emoji_merge.py` 設計 `extract_emoji_sequences()`
3. 先為 `👩‍💻`、`👋🏻`、`🇺🇸` 補來源字體測試
4. 先在 `Regular + Lite` 跑第一條 end-to-end

## 暫時不要重做的事

- 不用再重新調查 `🟡` / `🟢` 的 COLRv1 bug
- 不用再重新整理 `v1.5.2` / `v1.5.3` 歷史
- 不用再把 zip / png 驗證產物納入版本控制
