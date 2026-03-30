# v2.0 Sequence Emoji 實作設計

> 最後更新：2026-03-31
> 對應版本目標：`v2.0`
> 搭配閱讀：[`ROADMAP.md`](../ROADMAP.md)、[`src/emoji_merge.py`](../src/emoji_merge.py)

---

## 目標

v1.x 只支援單一 codepoint emoji。這代表：
- `😀` 這類單碼 emoji 可以 merge
- `👩‍💻`、`👋🏻`、`🇺🇸` 這類 sequence emoji 目前無法 merge

v2.0 的目標不是重寫三條 merge pipeline，而是補一層「sequence-aware metadata + GSUB 生成」能力，
讓 Color / Lite / COLRv1 都能共用同一份 sequence 規則。

---

## 目前 v1.x 資料流

```text
Noto emoji font
  |
  | getBestCmap()
  v
single codepoint -> glyph name
  |
  | collect deps / scale / rename
  v
merge into Sarasa glyph order
  |
  | update cmap
  v
output font
```

目前入口是 `get_emoji_cmap()`，只會拿到單一 codepoint。
這就是 ZWJ / 膚色 / 旗幟都缺席的根本原因。

---

## v2.0 需要的新資料流

```text
Noto emoji font
  |
  | A. read cmap
  | B. read GSUB ligatures
  v
single codepoint map
sequence map
  |
  | normalize into shared metadata
  v
emoji entry records
  - kind: single | sequence
  - codepoints: tuple[int, ...]
  - source glyph
  - variant dependencies
  |
  | merge glyph payloads into Sarasa
  | build GSUB ligature rules for sequences
  v
output font
  - cmap handles single codepoints
  - GSUB handles sequences
```

可以把它想成兩條路：
- `cmap` 負責單碼 emoji
- `GSUB ligature` 負責多碼 sequence emoji

---

## 建議新增的模組能力

### 1. Sequence 擷取

建議新增函式：

```text
extract_emoji_sequences(emoji_font) -> dict[tuple[int, ...], str]
```

責任：
- 讀來源字體 `GSUB`
- 專注處理 ligature substitution（LookupType 4）
- 建立 `codepoint sequence -> source glyph name`

說明：
- `👩‍💻` 不是 cmap 裡的一個 codepoint
- 它通常是多個輸入 glyph 經 GSUB 轉成一個 ligature glyph
- 所以一定要從 `GSUB` 抓，而不是從 `cmap` 抓

### 2. 共用資料模型

建議把目前分散在各 merge 分支中的 emoji 輸入，先收斂成共用 entry：

```text
EmojiEntry
  - codepoints: tuple[int, ...]
  - source_glyph: str
  - kind: "single" | "sequence"
  - source_table_kind: "CBDT" | "glyf" | "COLRv1"
```

三個變體都能吃這份 metadata，但實際複製內容不同：
- Color：copy bitmap + CBLC/CBDT references
- Lite：copy glyf outline + hmtx
- COLRv1：copy paint tree + helper glyphs + metrics

### 3. GSUB 生成

建議新增：

```text
build_ligature_gsub(sequence_entries, merged_cmap) -> GSUB fragments
merge_gsub_into_font(base_font, gsub_fragment)
```

責任：
- 把 sequence 轉成目標字體可用的 ligature rules
- sequence 中每個 codepoint 先經 cmap 找到 base glyph
- 再由 GSUB 將 glyph sequence 轉成 merged emoji glyph

概念圖：

```text
input text
  👩 + ZWJ + 💻
      |
      | shaping
      v
glyphs: uni1F469, uni200D, uni1F4BB
      |
      | GSUB ligature
      v
glyph: glyph_emoji_woman_technologist
```

---

## 這個專案最可能要改哪些檔案

### 必改

- [`src/emoji_merge.py`](../src/emoji_merge.py)
  - 新增 sequence extractor
  - 將 merge 流程從「只吃 cmap」擴充為「cmap + GSUB」
  - 讓三個變體共用 sequence metadata

- [`tests/test_emoji_merge.py`](../tests/test_emoji_merge.py)
  - 新增 sequence parser / GSUB builder pure logic tests

- [`tests/test_font_output.py`](../tests/test_font_output.py)
  - 新增 merged output font 的 sequence assertions

- [`verify-emoji.html`](../verify-emoji.html)
  - 新增 ZWJ / 膚色 / 旗幟專區

### 可能新增

- `src/emoji_sequences.py`
  - 如果不想讓 `emoji_merge.py` 再膨脹，建議把 sequence 解析與 GSUB 生成抽出去

---

## 建議的實作切法

### Phase 1: 先把來源 sequence 看懂

目標：
- 能從來源字體抓到一批 sequence
- 先不 merge，只驗證資料模型

完成條件：
- 測試能證明 `👩‍💻`、`👋🏻`、`🇺🇸` 存在於來源 sequence map

### Phase 2: 先支援 Regular + 一小組 MVP

MVP 建議：
- `👩‍💻`
- `👨‍💻`
- `👩‍🔬`
- `👋🏻`
- `🇺🇸`
- `👨‍👩‍👧‍👦`

目標：
- 只在 `Regular` 跑通 end-to-end
- 先在單一變體驗證設計可行，再擴到三變體

### Phase 3: 三變體接上同一套 sequence metadata

目標：
- Color / Lite / COLRv1 都能從同一組 sequence records 產生輸出
- 差異只留在 payload copy，不留在 sequence rule 定義

### Phase 4: 擴到全部 style 與 release 流程

目標：
- Regular / Italic / Bold / BoldItalic 一起支援
- 測試、verify、release workflow 一次補齊

---

## 主要風險點

### 1. 不是所有 sequence 都只是單純 ligature

有些 emoji 涉及：
- ZWJ
- variation selector
- skin tone modifier
- regional indicators

雖然都可以落到 sequence 處理，但資料前處理要先 normalize，否則測試會很難寫。

### 2. glyph rename 後，GSUB 指向也要同步

這個 repo 已經有 glyph rename 流程，尤其是 COLRv1 / BMP forced override。
v2.0 如果新增 sequence glyph，任何 rename 都必須同步更新 ligature 最終輸出 glyph name。

### 3. COLRv1 不能只複製主 glyph

對 COLRv1 而言，sequence emoji 仍可能依賴：
- paint tree
- LayerList
- helper glyphs
- helper metrics

也就是說，v1.5.2 修好的那類 helper metrics 問題，在 v2.0 仍然要小心，不是 sequence 做起來就自動安全。

### 4. shaping engine 相依

sequence emoji 是否成功，不只看字體檔本身，還取決於：
- HarfBuzz / browser shaping
- app 對 ZWJ / GSUB / COLRv1 的支援

所以 v2.0 必須同時有：
- 靜態 font 檢查
- 瀏覽器 verify 頁

---

## 測試建議

### pure logic

- sequence parser 能抓到來源 ligature
- regional indicator pair 能正確建 entry
- skin tone sequence 能正確 normalize

### output font

- merged font 含對應目標 glyph
- GSUB lookup 存在
- sequence shaping 後能落到正確 glyph name

### visual

verify 頁至少放三區：
- ZWJ：`👩‍💻 👨‍💻 👨‍👩‍👧‍👦`
- 膚色：`👋🏻 👍🏽 🙌🏿`
- 旗幟：`🇺🇸 🇯🇵 🇹🇼`

---

## 建議的第一張實作清單

1. 先新增 `extract_emoji_sequences()`
2. 為 `👩‍💻 / 👋🏻 / 🇺🇸` 寫來源字體測試
3. 決定 sequence metadata 結構
4. 先在 `Regular + Lite` 做第一條 end-to-end
5. 再把同一套 metadata 接到 Color / COLRv1
6. 最後才補 verify 頁與 release 流程

這樣切的原因是：
- Lite 最容易 debug
- Color / COLRv1 payload 較重，晚一點接入比較好收斂問題

---

## 與目前技術債的關係

v2.0 開工前，建議把下列事項視為同一組工程，而不是分散處理：

| 項目 | 是否屬於 v2.0 主線 |
|------|--------------------|
| 只支援單一 codepoint emoji | 是 |
| sequence 視覺驗證缺口 | 是 |
| output tests 只檢查 Regular | 部分相關 |
| CBLC filtering 可能移除有效 emoji | 否，屬 v1.x 既有 debt |

---

## 一句話結論

v2.0 的核心不是「再多搬一些 emoji 進來」，而是讓這個專案第一次具備
「從來源字體解析 sequence，並在輸出字體重建 GSUB ligature 規則」的能力。
