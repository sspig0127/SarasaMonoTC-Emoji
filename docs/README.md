# docs/ 目錄說明

本目錄存放 SarasaMonoTC-Emoji 專案的技術文件。依用途分為四類：

## 快速導覽

- **🎨 視覺預覽** — 想先看看 emoji 效果？參考 [預覽圖](#-視覺預覽)
- **🔍 規格決策** — 為什麼要設計 Nerd Lite？參考 [nerd-fonts-variant-eval.md](nerd-fonts-variant-eval.md)
- **📊 覆蓋率分析** — Nerd Lite 包含哪些圖示？參考 [nerd-fonts-coverage-analysis.md](nerd-fonts-coverage-analysis.md)
- **🏗 當前狀態** — 下一步開發方向？參考 [current-focus.md](current-focus.md)

---

## 文件分類

### 🟢 活躍維護（Active）
需要隨專案狀態持續更新的文件。

| 檔案 | 說明 |
|------|------|
| [current-focus.md](current-focus.md) | 當前開發狀態、下次開工建議、禁止重做清單 |
| [upstream-versions.json](upstream-versions.json) | 上游字體來源版本記錄，配合 `check-upstream.yml` workflow 使用 |

### 📋 技術決策記錄（Decision Record）
說明「為何做出這個設計選擇」的評估文件，未來開發相似功能時的必讀參考。

| 檔案 | 說明 |
|------|------|
| [v2-sequence-implementation.md](v2-sequence-implementation.md) | v2.0 ZWJ 序列 / 旗幟 / 膚色變體的 merge 架構設計 |
| [nerd-fonts-variant-eval.md](nerd-fonts-variant-eval.md) | Nerd Lite 第四變體的架構評估（為何選擇 PUA merge 方案） |
| [nerd-fonts-coverage-analysis.md](nerd-fonts-coverage-analysis.md) | Nerd Fonts Symbols Only 覆蓋率分析（當前 32% 覆蓋；設計決策 + 改進方案） |
| [colrv1-budget-expansion-eval.md](colrv1-budget-expansion-eval.md) | COLRv1 glyph budget 擴增可行性分析（v2.2） |
| [openmoji-coverage-eval.md](openmoji-coverage-eval.md) | OpenMoji 黑白 SVG 替換 Lite glyph 源的覆蓋率評估（2026-04-06；OpenMoji 16.0.0 vs noto-emoji v2.051） |

### 📦 建構產物（Build Artifact）
由 `build.py` 自動產生，不要手動修改。

| 檔案 | 說明 |
|------|------|
| [colrv1-emoji-list.json](colrv1-emoji-list.json) | COLRv1 變體目前選入的 emoji 清單（`build.py --colrv1` 產物） |

### 🗂 開發歷史（History）
已完成開發階段的實作記錄與研究素材，供查閱技術決策背景。日常開發不需要主動閱讀。

| 檔案 | 說明 |
|------|------|
| [roadmap-history.md](roadmap-history.md) | v1.x–v2.3 各版本實作細節（從 ROADMAP.md 分離存檔） |
| [nerd-lite-impl-plan.md](nerd-lite-impl-plan.md) | v2.1 Nerd Lite MVP 實作計畫（已完成，merge 至 main） |
| [release-notes-v2.2.0.md](release-notes-v2.2.0.md) | v2.2.0 release notes 草稿 |
| [about_SarasaMonoTCEmojiLite+Nerd_Font_icon.md](about_SarasaMonoTCEmojiLite+Nerd_Font_icon.md) | Nerd Lite 構想期的 Perplexity 研究對話 |

---

## 🎨 視覺預覽

四個變體的 emoji 覆蓋率與 Nerd Lite 專屬圖示展示。完整預覽圖存放於 [`preview/`](preview/) 目錄。

### emoji 分類對照

| 類別 | 預覽圖 |
|------|--------|
| 📊 統計摘要與分類概觀 | [preview/00_Summary_statistics.png](preview/00_Summary_statistics.png) |
| 😀 Smileys & Emotion | [preview/01_Smileys_Emotion.png](preview/01_Smileys_Emotion.png) |
| 👋 People & Body | [preview/02_People_Body.png](preview/02_People_Body.png) |
| 🐶 Animals & Nature | [preview/03_Animals_Nautre.png](preview/03_Animals_Nautre.png) |
| 🍎 Food & Drink | [preview/04_Food_Drink.png](preview/04_Food_Drink.png) |
| ✈️ Travel & Places | [preview/05_Travel_Places.png](preview/05_Travel_Places.png) |
| ⚽ Activities | [preview/06_Activities.png](preview/06_Activities.png) |
| 💡 Objects | [preview/07_Objects.png](preview/07_Objects.png) |
| ❤ Symbols | [preview/08_Symbols.png](preview/08_Symbols.png) |
| 🚩 Flags | [preview/09_Flags.png](preview/09_Flags.png) |
| 👨‍👩‍👧 ZWJ Sequences | [preview/10_ZWJ.png](preview/10_ZWJ.png) |

### Nerd Lite 專屬圖示

**Nerd Lite 變體**獨有的開發圖示（4 大集合，1,226 個圖示）：

| 集合 | 預覽圖 | 說明 |
|------|--------|------|
| 🔶 Powerline Symbols | [preview/11_Nerd_Fonts_PUA_icons_01.png](preview/11_Nerd_Fonts_PUA_icons_01.png) | Shell prompt 分隔符（1 欄寬） |
| 🔷 Devicons | [preview/11_Nerd_Fonts_PUA_icons_02.png](preview/11_Nerd_Fonts_PUA_icons_02.png) | 編程語言、框架 logo（2 欄寬） |
| 🟨 Codicons & Octicons | [preview/11_Nerd_Fonts_PUA_icons_03.png](preview/11_Nerd_Fonts_PUA_icons_03.png) | VS Code、GitHub icon（2 欄寬） |

> 想深入瞭解覆蓋率細節？參考 [nerd-fonts-coverage-analysis.md](nerd-fonts-coverage-analysis.md) — 解釋為什麼只覆蓋 32%，以及是否需要補充其他圖示。

---

## YAML Front Matter 標籤說明

各文件頂部使用以下 YAML front matter 標記元資訊：

```yaml
---
type: active | decision-record | build-artifact | history
status: current | archived
version: v2.x          # 此文件所屬的版本里程碑
audience: maintainer | future-developer | auto-generated
---
```

| 欄位 | 說明 |
|------|------|
| `type` | 文件用途分類（同上四類） |
| `status` | `current` 表示仍有效；`archived` 表示已封存 |
| `version` | 此文件最主要對應的版本 |
| `audience` | `maintainer` = 日常維護用；`future-developer` = 建議有相似需求的開發者閱讀；`auto-generated` = 建構產物 |
