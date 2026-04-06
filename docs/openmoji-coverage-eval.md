---
type: decision-record
status: current
version: v2.x
audience: future-developer
---

# OpenMoji 黑白 SVG 替換 Lite glyph 源：覆蓋率評估

> 評估日期：2026-04-06
> 對應 ROADMAP 項目：長期觀察 → OpenMoji 替代 Lite glyph 源
> 評估腳本：`check_emoji_coverage.py`（根目錄）

## 評估版本

| 來源 | 版本 |
|------|------|
| OpenMoji（黑白 SVG）| **16.0.0** |
| noto-emoji（現行 Lite 來源）| **v2.051**（commit `8998f5dd`） |

---

## 覆蓋率結果

| emoji 類型 | OpenMoji 覆蓋 noto-emoji | OpenMoji 有 | noto-emoji 有 | 缺少數量 |
|-----------|--------------------------|------------|--------------|---------|
| 全部 | **73.49%** | 4,490 | 3,731 | 989 |
| ZWJ 序列 | **40.46%** | 1,664 | 1,614 | 961 |
| 膚色變體 | **59.95%** | 2,035 | 2,035 | 815 |
| ZWJ 或膚色（聯集）| **57.92%** | — | 2,284 | 961 |
| ZWJ + 膚色（同時）| **40.29%** | — | 1,365 | 815 |

> 注意：`missing_in_openmoji_count` 中包含 `0023`、`002A`、`0030`–`0039`（ASCII #、*、0–9 的獨立 SVG），這些本來就不應被轉成 emoji，屬於統計上的偽陽性，真實缺口略少於 989。

---

## 關鍵發現

### ZWJ 缺口過大（40% 覆蓋率）

961 個 ZWJ 序列在 OpenMoji 中缺失，主要包括：
- 職業 + 性別 + 膚色三重組合（如 `👩🏽‍💻` woman technologist medium skin）
- 方向性 ZWJ（如 `🏃🏻‍♂️‍➡️` man running light skin facing right）
- 部分家庭 emoji 變體

這些正是本專案 v2.0（ZWJ merge）、v2.3（Chromium composite 修復）所花工夫支援的部分，**若換源後這些 emoji 會全部缺失**。

### 單碼 emoji 品質有優勢

OpenMoji 黑白 SVG 的設計原生為單色，線條一致性優於 Noto 彩色降色結果。對不涉及 ZWJ 或膚色的基本 emoji，OpenMoji 是更好的視覺來源。

---

## 可行方案評估

### 方案 A：完全替換（❌ 不可行）

直接以 OpenMoji 取代 Noto，ZWJ 序列缺口 961 個，影響大量常用 emoji，不可行。

### 方案 B：混合來源（⚠️ 可行但工作量高）

| 來源 | 負責範圍 |
|------|---------|
| OpenMoji black SVG | 單碼 emoji（品質提升，無降色失真） |
| Noto（現行）| ZWJ 序列、膚色變體、旗幟 |

**優點**：不損失覆蓋率，單碼 emoji 視覺品質提升  
**缺點**：pipeline 需支援雙來源，複雜度大幅增加；ZWJ 與單碼的 glyph 風格可能不統一

### 方案 C：等待 OpenMoji 提升 ZWJ 覆蓋（⏳ 長期觀察）

追蹤 OpenMoji 版本更新，若未來 ZWJ 覆蓋率提升至 80%+ 以上，再重新評估完全替換。目前 16.0.0 的 40% ZWJ 覆蓋不足以支撐替換。

---

## 結論

**現階段建議維持現行 Noto 方案，不啟動 OpenMoji 替換工程。**

可考慮的低風險行動：
- 將 OpenMoji 覆蓋率追蹤加入 `check-upstream.yml`（追蹤 `hfg-gmuend/openmoji` 是否有新版）
- 等 OpenMoji ZWJ 覆蓋率超過 80% 再重新評估

---

## 附：評估腳本說明

`check_emoji_coverage.py` 比較兩個 SVG 目錄的檔名：

```
noto-emoji/svg/          → emoji_uXXXX_XXXX.svg 格式（需 strip emoji_u 前綴、_ 改 -）
openmoji/black/svg/      → XXXX-XXXX.svg 格式
```

輸出存於 `output/openmoji_noto_coverage.json`。
