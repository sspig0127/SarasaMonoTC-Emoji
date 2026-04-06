# Nerd Fonts Symbols Only 覆蓋率分析

## 摘要

**Nerd Fonts Symbols Only** 是一個專門為開發者設計的字體，包含多個開發相關的圖示集合。您的 **Nerd Lite 變體目前的覆蓋率約為 32%**（1,131 / 3,500 codepoints）。

## 詳細數據

### 當前 Nerd Lite 配置

```
U+E0A0–U+E0D7:   40/  56 ❌ Powerline（部分缺失）
U+E5FA–U+E6FF:  191/ 262 ❌ Seti-UI + Custom（部分缺失）
U+E700–U+E7FF:  256/ 256 ✓ Devicons（完整）
U+EA60–U+EBEB:  388/ 396 ❌ Codicons（部分缺失）
U+F400–U+F4FF:  256/ 256 ✓ Octicons（完整）

總計：1,131 / 3,500 codepoints = 32.3%
```

### 實際字體中可用但未被配置的 Ranges

| Range | 數量 | 集合名稱 |
|-------|------|---------|
| U+E000–U+E00A | 11 | Nerd Fonts 內部符號 |
| U+E200–U+E2A9 | 170 | (未知集合，可能是早期 Nerd Fonts) |
| U+E300–U+E3E3 | 228 | (未知集合) |
| U+E800–U+E8EF | 240 | Devicons 延伸（當前配置範圍外） |
| U+EBEC–U+EC1E | 51 | Codicons 延伸（當前配置範圍外） |
| U+ED00–U+EFCE | 719 | Material Design Icons（官方 v3.x+） |
| U+F000–U+F381 | 898 | Font Awesome 5 Extended |
| U+F500–U+F533 | 52 | Font Awesome 6 / 後續版本 |

**共計 2,369 個未被包含的 codepoints**

## 為什麼只覆蓋了部分？

### 1. 設計決策（intentional）
- **文件尺寸優化**：Nerd Lite 的目標是「精選最實用的開發圖示」，而非「完整 Nerd Fonts 覆蓋」
- **終端機可讀性**：Material Design Icons（719 個）和 Font Awesome（898 + 898 = ~1,700+ 個）都較複雜，在小字體尺寸下難以辨識
- **維護負擔**：覆蓋所有 3,500+ 圖示會大幅增加字體檔案大小（目前 ~26 MB，可能增至 30–35 MB）

### 2. 實現層面
- **當前範圍選擇**：
  - Powerline（56 個）— 終端機 prompt 分隔符
  - Devicons（256 個）— 編程語言、框架
  - Seti-UI（262 個）— 檔案類型 icon
  - Codicons（396 個）— VS Code icon
  - Octicons（256 個）— GitHub icon
  
- **這 5 個集合涵蓋了日常開發中最常用的 ~1,200 個圖示**

## Nerd Fonts 官方完整集合（已知）

Nerd Fonts v3.4.0（當前版本）包含：

| 集合 | Codepoint 範圍 | 數量 | 說明 |
|------|---------------|------|------|
| Powerline | E0A0–E0D7 | 56 | Shell prompt 分隔符 |
| Powerline Extra | E0DE–E0FF | 34 | 額外符號（當前未覆蓋） |
| Seti-UI | E5FA–E6FF | 262 | 檔案類型圖示 |
| Devicons | E700–E7FF | 256 | 編程語言 logo |
| Font Logos | E300–E3E3 | 228 | 技術公司 logo（部分未覆蓋） |
| Codicons | EA60–EBEB | 396 | VS Code icon |
| Octicons | F400–F4FF | 256 | GitHub icon |
| Material Design | ED00–EFCE | 719 | 材料設計圖示（未覆蓋） |
| Font Awesome 5 | F000–F381 | 898 | Font Awesome 5（未覆蓋） |
| Font Awesome 6 | F300–F313, F500–F8FF | ~1,100+ | Font Awesome 6（部分未覆蓋） |

**官方合計：~3,500+ codepoints**

## 建議

### ✓ 當前狀態足夠嗎？

**對於大多數開發者：YES** ✓
- Nerd Lite 的 1,226 個精選圖示已涵蓋日常終端機使用場景
- Powerline、Devicons、Codicons、Octicons 是最常用的集合
- Material Design / Font Awesome 通常用於 GUI 應用，不是終端機主流

### ⚠️ 考慮補充的情況

若您需要以下圖示，建議擴展配置：

1. **Font Awesome 5 / 6**（U+F000–U+F8FF）
   - 圖示數量多（900+），但文件大小會增加 2–3 MB
   - 適合做成**獨立選項**（e.g., `--nerd-full` 標籤）

2. **Material Design Icons**（U+ED00–U+EFCE）
   - 非終端機主流，適合 GUI 場景
   - 檔案大小增加 ~2 MB

3. **Powerline Extra**（U+E0DE–U+E0FF）
   - 只有 34 個，可輕鬆補充（無顯著大小增加）

### 📋 改進方案（可選）

#### 方案 A：最小化補充（推薦）
```yaml
icon_ranges:
  - [0xE0A0, 0xE0FF]   # Powerline + Extra（原 E0D7 擴至 E0FF）
  - [0xE5FA, 0xE6FF]   # Seti-UI + Custom
  - [0xE700, 0xE7FF]   # Devicons
  - [0xEA60, 0xEBEB]   # Codicons
  - [0xF400, 0xF4FF]   # Octicons
```
**增加：34 個 Powerline Extra 圖示，檔案大小 +100 KB**

#### 方案 B：含 Font Awesome
```yaml
icon_ranges:
  - [0xE0A0, 0xE0FF]   # Powerline + Extra
  - [0xE5FA, 0xE6FF]   # Seti-UI + Custom
  - [0xE700, 0xE7FF]   # Devicons
  - [0xEA60, 0xEBEB]   # Codicons
  - [0xED00, 0xEFCE]   # Material Design
  - [0xF000, 0xF381]   # Font Awesome 5
  - [0xF400, 0xF4FF]   # Octicons
  - [0xF500, 0xF8FF]   # Font Awesome 6
```
**增加：2,800+ 圖示，檔案大小 +3–4 MB（總計 ~29–30 MB）**

#### 方案 C：建立變體選項
- `SarasaMonoTCEmojiLiteNerd`（當前，32% 覆蓋，~26 MB）
- `SarasaMonoTCEmojiLiteNerdFull`（新增選項，100% 覆蓋，~30 MB）

---

## 結論

**您的 Nerd Lite 變體目前的覆蓋率（32%）是有意設計的權衡**，優先選擇在終端機中最實用、最常見的圖示集合。若需要完整覆蓋或特定的補充圖示，可考慮上述改進方案。
