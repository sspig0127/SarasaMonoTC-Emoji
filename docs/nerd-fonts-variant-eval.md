---
type: decision-record
status: current
version: v2.1
audience: future-developer
---

# Nerd Fonts 變體評估

> 建立：2026-04-04
> 依據：ROADMAP.md v2.x 評估項目、Perplexity 建議（`docs/about_SarasaMonoTCEmojiLite+Nerd_Font_icon.md`）

## 摘要

本文評估在 SarasaMonoTC-Emoji 基礎上整合 Nerd Fonts PUA icon 的可行路線，
提供架構選項比較、技術限制分析與建議優先方向。

---

## 來源字體現況

來源字體：`fonts/NerdFontsSymbolsOnly/SymbolsNerdFontMono-Regular.ttf`

| 項目 | 數值 |
|------|------|
| UPM | 2048 |
| 總 glyph 數 | 10,413 |
| BMP PUA（E000–F8FF） | 3,500 glyphs |
| Plane 15 PUA（F0001–F1AF0） | 6,896 glyphs（Material Design Icons 全集） |

### BMP PUA 分區明細

| icon 集 | 碼位區間 | glyph 數 | 開發者常用性 |
|---------|---------|---------|------------|
| Powerline Symbols | E0A0–E0D7 | 40 | ⭐⭐⭐ 最高（prompt 分隔符、branch） |
| Devicons | E700–E7FF | 256 | ⭐⭐⭐ 語言 logo（Python、JS、Go、Rust、Docker）|
| Codicons | EA60–EBEB | 388 | ⭐⭐⭐ VS Code 圖示集 |
| Octicons | F400–F4FF | 256 | ⭐⭐ GitHub（PR、issue、branch）|
| Seti-UI + Custom | E5FA–E6FF | 191 | ⭐⭐ 編輯器檔案類型 |
| Font Awesome | F000–F2FF | 768 | ⭐⭐ 通用 UI（git、資料夾、檔案）|
| Font Awesome Extension | E200–E2FF | 170 | ⭐ 補充 icon |
| Weather | E300–E3FF | 228 | ⭐ 氣象 icon（wttr.in、waybar）|
| Font Linux | F300–F31F | 32 | ⭐ Linux distro logo |
| Pomicons | E000–E00A | 11 | 低 |
| Material Design（BMP） | F500–FD46 | 52 | 低 |

---

## 架構選項比較

### 選項 A：字型 fallback（不修改字體，使用者自行疊加）

字型堆疊：`SarasaMonoTCEmojiLite, Symbols Nerd Font Mono`

| 面向 | 評估 |
|------|------|
| 開發成本 | ✅ 零工程成本 |
| 使用者門檻 | ⚠️ 需安裝兩個字體並自行設定 |
| VHS 相容性 | ⚠️ 取決於環境 fallback 機制是否完整 |
| 維護成本 | ✅ 最低 |
| 適用情境 | 本機終端機（WezTerm、kitty、Ghostty 等支援 fallback 的環境） |

**結論**：適合個人使用者，不適合作為發布字體目標（使用者仍需自行設定）。

### 選項 B：從 Lite 變體擴增（新增 SarasaMonoTCEmojiLiteNerd）

以現有 `merge_emoji_lite()` pipeline 為基礎，加入 Nerd Fonts PUA glyph merge step。

| 面向 | 評估 |
|------|------|
| 開發成本 | ⚠️ 中等（新增 `merge_emoji_lite_nerd()` 或加旗標） |
| 單一字體 | ✅ 使用者只需裝一個字體 |
| VHS 相容性 | ✅ 繼承 Lite 的 glyf 相容性 |
| 檔案大小 | ⚠️ Lite 約 25 MB，加 PUA 後預計 +3–8 MB（依選取 glyph 數量） |
| Bold / Italic | ⚠️ 四個 style 都要確認 icon 縮放一致（Nerd Fonts 各 style 用同一 icon） |
| 維護成本 | ⚠️ 需跟 Nerd Fonts 版本同步 |

**結論**：優先推薦。與目標場景（VHS / 終端機）高度吻合，開發成本可控。

### 選項 C：全新獨立變體（SarasaMonoTCEmojiNerd，從 base Sarasa 出發）

獨立 pipeline，同時 merge emoji + Nerd Fonts PUA，不依賴現有 Lite pipeline。

| 面向 | 評估 |
|------|------|
| 開發成本 | ❌ 最高 |
| 彈性 | ✅ 可自由選擇 emoji 格式（glyf / COLRv1） |
| 維護成本 | ❌ 高，三套 pipeline 各自需維護 |

**結論**：中長期選項，短期不建議。

---

## 技術限制分析

### UPM 差異（關鍵）

| 字體 | UPM |
|------|-----|
| Nerd Fonts Symbols Mono | **2048** |
| Sarasa / 現有輸出字體 | **1000** |

merge 時需對 Nerd glyph 做 UPM 縮放（scale factor = 1000 / 2048 ≈ 0.4883）。
主要影響：glyph outline 座標、`hmtx` advance width / lsb。

參考：COLRv1 merge 已有 `_scale_colrv1_paint_coords()` 處理相同問題；
glyf 版本縮放相對簡單（TrueType outline 座標直接乘以 scale factor）。

### 字寬一致性

Nerd Fonts Mono 的 advance width 通常為 1024（UPM 2048 的一半，對應 1 欄 monospace）。
縮放後預計 ≈ 500，符合 Sarasa 的 half-width 設計。

需驗證的邊界情況：
- advance width 不是整數的 icon（縮放後 rounding）
- 有雙寬設計的 icon（如部分 Powerline separator）

### glyph 數量與範圍選擇

Lite 沒有像 COLRv1 的 glyph 預算限制，但建議不要全量（10,410 個）：

| 策略 | glyph 數 | 說明 |
|------|---------|------|
| 開發者核心子集 | ~200–400 | Powerline + Devicons + Codicons + Octicons |
| BMP PUA 全量 | 3,500 | 涵蓋大多數 icon 集 |
| 全量（含 Plane 15） | 10,410 | Material Design Icons 全集，大多終端機用不到 |

**建議**：MVP 從開發者核心子集開始，驗證後決定是否擴充至 BMP 全量。

### PUA 碼位衝突

目前三個變體（Color / Lite / COLRv1）均未使用 PUA 區段，無碰撞風險。

---

## 建議路線

### Phase 1：MVP 驗證（Lite 擴增，Regular only）

**目標 icon 集**（約 200–300 個 BMP PUA glyph）：

| 優先級 | 集合 | glyph 數 | 理由 |
|-------|------|---------|------|
| P1 | Powerline Symbols | 40 | prompt / 分隔符，幾乎所有開發者用 |
| P1 | Devicons | 256 | 語言 logo，Neovim / 檔案管理器必備 |
| P2 | Codicons | 388 | VS Code 整合場景 |
| P2 | Octicons | 256 | Git / GitHub 相關 |
| P3 | Seti-UI | 191 | 編輯器檔案類型 |
| 暫緩 | Font Awesome | 768 | 數量大，先評估 P1-P3 再說 |
| 暫緩 | Plane 15 | 6,896 | 終端機場景用量低 |

**驗證清單**：
1. UPM 縮放後 icon 輪廓正確（不失真、不裁切）
2. advance width = 500（符合半寬 monospace）
3. 終端機顯示（WezTerm / iTerm2 / kitty）
4. VHS 錄影顯示（Headless Chromium + xterm.js）
5. `verify-emoji.html` 新增 Nerd 變體切換區塊

### Phase 2：決定完整範圍與發布策略

MVP 通過後評估：
- 是否擴充至 BMP PUA 全量（3,500 glyphs）
- Plane 15 是否有需求
- Bold / Italic / BoldItalic icon 一致性確認
- 發布字族名稱：`SarasaMonoTCEmojiLiteNerd` 或 `SarasaMonoTCEmojiNerd`
- `config.yaml` 設計（是否獨立 `nerd:` section）

---

## 風險清單

| 風險 | 說明 | 緩解 |
|------|------|------|
| UPM 縮放 rounding | 2048→1000 縮放後 glyph 可能有像素級誤差 | MVP 用少量 icon 先目視驗證 |
| advance width 不符合 mono | 部分 icon 不是標準 1024 advance | build 時檢查並強制修正 |
| Nerd Fonts 版本更新 | 新版碼位可能移動 | 鎖定版本，在 `config.yaml` 記錄來源版本 |
| Bold / Italic 不一致 | Nerd Fonts 各 style 共用同一 icon 設計 | 確認 Regular icon 在其他 style 視覺可接受 |
| 授權合規 | Nerd Fonts MIT，來源 icon 集授權各異 | 確認各子集授權（多數為 MIT / OFL / Apache 2.0）；在 README 揭露 |
| 維護負擔 | 多一條 merge pipeline | 設計成 Lite 的「可選旗標」，共用基礎架構 |

---

## 結論

**短期建議**：選擇「選項 B」（Lite 擴增），從 Powerline + Devicons + Codicons + Octicons 開始 MVP 驗證。

不建議立即做：
- Color / COLRv1 變體加入 Nerd merge（等 MVP 結果再評估）
- 全量導入 10,410 個 glyph（先聚焦開發者核心子集）
- Plane 15 PUA（Material Design Icons 在終端機場景需求低）
- 依賴 fallback 作為發布策略（不解決使用者需要自行設定的問題）

**下一步**：若決定啟動 MVP，建議建立獨立分支（`feature/nerd-lite-mvp`）進行，不影響主線穩定性。
