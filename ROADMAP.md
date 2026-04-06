# SarasaMonoTC-Emoji 路線圖

> 最後更新：2026-04-06（v2.3.0 已發佈；Ghostty 相容性 Lite / Nerd Lite 驗證通過；CBLC name-conflict 技術債解決）
>
> **歷史版本實作細節** → [`docs/roadmap-history.md`](./docs/roadmap-history.md)（需要查閱時再 Read）
> **COLRv1 深度技術細節** → [`.github/colrv1-dev-notes.md`](./.github/colrv1-dev-notes.md)
> **v2.0 實作設計** → [`docs/v2-sequence-implementation.md`](./docs/v2-sequence-implementation.md)

---

## 版本規劃概覽

| 版本 | 重點 | 狀態 |
|------|------|------|
| v1.0–v1.3 | Color / Lite 變體、測試框架 | ✅ 已發佈 |
| v1.4 | COLRv1 第三變體（彩色向量） | ✅ 已發佈 |
| v1.4.1 | COLRv1 greedy 選取（修復網頁亂碼） | ✅ 完成 |
| v1.4.2 | COLRv1 priority allowlist（dev emoji 保證彩色） | ✅ 已發佈 |
| v1.5 | BMP 符號彩色覆蓋；post 3.0→2.0 升級；75 tests | ✅ 完成 |
| v1.5.1 | force BMP 清單 5→15；Budget 8132→8091 slots | ✅ 完成 |
| **v1.5.2** | COLRv1 paint 座標 + helper metrics 修復（🟡🟢 Chromium 渲染回歸） | ✅ 完成 |
| **v1.5.3** | COLRv1 高風險樣本驗證頁 + 全域 transformed-helper regression test | ✅ 完成 |
| v2.0 | ZWJ 序列 / 旗幟 / 膚色變體 + release workflow 收尾 | ✅ 已發佈 |
| v2.1 | 第四變體 Nerd Lite（Emoji + Nerd Fonts PUA） | ✅ 已發佈 |
| **v2.2** | COLRv1 budget 擴增（skip-and-continue greedy + 221 sequences） | ✅ 已發佈 |
| **v2.3** | 家庭 emoji 全人物渲染修復（Chromium TrueType composite bug 繞過）；200 tests | ✅ 已發佈 |
| v2.x | 後續維護 / 技術債 | 📋 進行中 |

---

## v2.0 — 完整 Emoji 支援（已發佈，細節已歸檔）

ZWJ 序列 / 旗幟 / 膚色變體全面支援。四條 merge pipeline 已全部串通。

> 實作細節 → [`docs/roadmap-history.md`](./docs/roadmap-history.md)
> Sequence 設計 → [`docs/v2-sequence-implementation.md`](./docs/v2-sequence-implementation.md)

---

## v2.1 — Nerd Lite 第四變體（已發佈）

字族名稱：`SarasaMonoTCEmojiLiteNerd`；建構指令：`uv run python build.py --nerd-lite`

以 Lite 為底，合併 Nerd Fonts BMP PUA icon（Powerline / Devicons / Codicons / Octicons / Seti-UI），讓單一字體同時具備中文、emoji 與常用開發圖示。

**折衷方案（PUA 欄寬）**：Powerline（E0A0–E0D7）1 欄（prompt 對齊），其他集合 2 欄（視覺比例與 emoji 一致）

> 實作細節 → [`docs/roadmap-history.md`](./docs/roadmap-history.md)
> 架構評估 → [`docs/nerd-fonts-variant-eval.md`](./docs/nerd-fonts-variant-eval.md)

---

## v2.3 — 家庭 emoji 全人物渲染修復（已發佈）

**問題**：`👨‍👩‍👧‍👦` / `👨‍👩‍👧` / `👩‍👧‍👦` 等多人 ZWJ emoji 在 Chromium 系瀏覽器（VS Code webview / xterm.js / VHS）只顯示部分人物，最左側人物被截斷。

**根本原因（Chromium TrueType composite bug）**：Chromium 解析 TrueType composite 字形時，若同一 composite 的 component 清單中 argument encoding 從 16-bit（|offset| > 127）切換為 8-bit（|offset| ≤ 127），前面的 16-bit component 會被靜默跳過。以 `👨‍👩‍👧‍👦` 為例，4 個 component 的 X offset 分別為 225 / 447 / **-9** / -229，offset -9 觸發 8-bit encoding，導致 offset 225 與 447 的 component 不被渲染。

**解法**：`emoji_merge.py` 在所有後處理步驟完成後，自動偵測含有 |offset| > 127 component 的 composite 字形，以 `fontTools.Glyph.getCoordinates()` 遞迴展開所有 component，重建為 single simple glyph，消除 composite 結構。29 個家庭 / 多人組合受益；小 offset composite（PoC 旗幟字形）不受影響。

**額外修正**：
- 左邊界保護：scale-down 後 xMin < 120 font units 的字形自動右移，避免最左側人物在小字體下因 sub-pixel rounding 被剪裁
- hmtx lsb 在所有調整後同步至實際 xMin
- 新增回歸測試 `test_no_overflow_composite_ligatures`（200 tests 總計）

---

## v2.x — 後續維護 / 技術債

- 追蹤 `astral-sh/setup-uv` node24 版，屆時更新 release workflow
- 上游版本追蹤已自動化（`check-upstream.yml`）；Sarasa Gothic 已升至 v1.0.37
- COLRv1 budget 幾乎已滿，不建議再輕易擴增：
  - config 緩衝：8,450 − 8,327 = **123 slots**（單碼 emoji 成本 10–100，實際空間極有限）
  - TrueType 硬上限距離：65,535 − Italic 65,232 = **303 slots**（絕對上限）
  - 若要再加，只適合 cost=1 的 sequence（components 已全部選入者）
- ~~補 Italic / Bold / BoldItalic output font 自動化測試~~（✅ 已完成，200 tests）
- ~~評估 Emoji 17.0 / Nerd Fonts 版本更新~~（✅ 已自動化：`check-upstream.yml` 每月 1 日偵測三個上游，有新版自動開 issue）

---

## 中長期評估方向

> 來源：2026-04-04 社群趨勢調查。各項依優先度排列，非承諾清單。

### 近期可評估（低工作量）

| 項目 | 說明 |
|------|------|
| **Emoji 17.0 跟進** | Unicode 17.0（2025-09）新增 163 個 emoji，含新 ZWJ 序列與膚色組合。**✅ 已自動化**：`check-upstream.yml` 每月偵測 `googlefonts/noto-emoji`，有新版自動開 issue；收到通知後下載新版字體、重跑建構即可覆蓋 |
| **Nerd Fonts 版本定期追蹤** | Nerd Fonts 3.x 持續更新；部分 icon（Material Design Icons）已遷移至新 PUA-A 段，舊 codepoint 棄用。**✅ 已自動化**：`check-upstream.yml` 每月偵測 `ryanoasis/nerd-fonts`（目前採用 v3.4.0）；收到通知後確認 PUA 段有無 breaking change，再更新 NerdFontsSymbolsOnly.zip |
| ~~**Ghostty 相容性驗證**~~ | ✅ v2.3 後已確認：Lite / Nerd Lite 在 Ghostty 少量測試通過，無 cursor desync 或 emoji 寬度異常。Color / COLRv1 未另行驗證（bitmap / COLRv1 在終端機環境本即次要） |

### 中期可評估（中工作量）

| 項目 | 說明 |
|------|------|
| **COLRv1 glyph budget 擴充** | ✅ v2.2 已完成：skip-and-continue greedy、10 priority emoji（📏📐📝📜📕📗📘📙📔🕑）、221 priority sequences；8,327/8,450 slots，剩餘 123。評估細節 → [`docs/colrv1-budget-expansion-eval.md`](./docs/colrv1-budget-expansion-eval.md) |

### 長期觀察（高工作量 / 需外部條件）

| 項目 | 說明 |
|------|------|
| **CBDT 長期策略** | Android / Fedora 已遷移 COLRv1，CBDT 在非 Android 場景優先度持續下降。觀察生態系，評估未來是否降格 Color 變體為相容性備援 |
| **Variable Font 探索** | 需依賴 Sarasa Gothic 上游提供 Variable 版本；目前條件不具備，列為長期觀察。Sarasa 版本更新已由 `check-upstream.yml` 自動偵測，收到 issue 通知時人工確認該版本是否引入 Variable 格式 |
| **OpenMoji 替代 Lite glyph 源** | OpenMoji 黑白 SVG 風格一致，可能優於 Noto 彩色降色結果；需建立 SVG→glyf 轉換管線，工作量高 |

---

## 待解技術債

| 項目 | 位置 | 說明 |
|------|------|------|
| ~~CBLC filtering 可能移除有效 emoji~~ | `emoji_merge.py:_filter_cblc_to_added_glyphs` | ✅ 2026-04-06 解決：新增 103 項至 `force_color_codepoints`（71 BMP + 32 非 BMP），衝突從 127 → 24。剩餘 24 項均為有意保留 monochrome：ASCII 數字/標點、card suit、©®™、♀♂、控制字元、helper glyph |
| COLRv1 sequence 仍為 budget-limited | `config.yaml`、`emoji_merge.py:merge_emoji_colrv1` | v2.2 已擴增至 811（8,327/8,450），config 剩餘 **123 slots**；單碼 emoji 成本通常 10–100 slots，實際上幾乎已滿，只夠加少量 cost=1 sequence |
