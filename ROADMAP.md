# SarasaMonoTC-Emoji 路線圖

> 最後更新：2026-03-30（v1.5.3 完成；COLRv1 驗證與回歸覆蓋補強）
>
> **歷史版本實作細節** → [`docs/roadmap-history.md`](./docs/roadmap-history.md)（需要查閱時再 Read）
> **COLRv1 深度技術細節** → [`.github/colrv1-dev-notes.md`](./.github/colrv1-dev-notes.md)

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
| v2.0 | ZWJ 序列 / 旗幟 / 膚色變體 | 🔮 未來 |

---

## v2.0 — 完整 Emoji 支援（長期）

目前約 40% 現代 emoji 因需要 ZWJ 序列而缺席。v2.0 目標是補齊這個缺口。

| 類型 | 範例 | 技術需求 |
|------|------|---------|
| 膚色變體 | 👋🏻 | codepoint sequence → GSUB ligature |
| ZWJ 家庭 | 👨‍👩‍👧‍👦 | ZWJ（U+200D）序列 |
| 旗幟 | 🇺🇸 | Regional Indicator 雙字元 |
| 性別 / 職業 | 👩‍💻 | ZWJ + U+2640/2642 |

**技術方向**：解析 NotoColorEmoji GSUB（LookupType 4），建立 ZWJ sequence → glyph 對應，
加入 GSUB ligature rules。參考：[noto-emoji add_emoji_gsub.py](https://github.com/googlefonts/noto-emoji/blob/main/add_emoji_gsub.py)

---

## 待解技術債

| 項目 | 位置 | 說明 |
|------|------|------|
| CBLC filtering 可能移除有效 emoji | `emoji_merge.py:_filter_cblc_to_added_glyphs` | 名稱衝突時捨棄 color bitmap。Build log 列出被移除的 glyph 名稱（最多 10 個），可評估是否需加入 `force_color_codepoints` |
