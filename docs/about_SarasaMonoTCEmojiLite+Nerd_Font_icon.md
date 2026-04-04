<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# 我希望 以 SarasaMonoTCEmojiLite 為基礎, 加上 Nerd Font icons.  期待能夠在VHS 做終端機錄影 或其他終端機介面的軟體可以正常顯示icon

可以，這個方向是對的：**以 `SarasaMonoTCEmojiLite` 當主字型，再另外補一層 `Symbols Nerd Font Mono` 當 fallback**，通常比直接把整套 Sarasa patch 成 Nerd Font 更穩，特別適合 VHS、xterm.js、以及其他吃 Chromium renderer 的終端機介面。[^1][^2][^3]

## 建議架構

你的需求其實可以拆成兩件事：

- `SarasaMonoTCEmojiLite` 負責：繁中字形、等寬英文、單色 emoji、ZWJ／膚色／旗幟等 sequence emoji，而且 Lite 變體明確是為 VHS / xterm.js / Headless Chromium 相容性而設計的。[^1]
- `Symbols Nerd Font Mono` 負責：Nerd Font 的 PUA icons，也就是 Neovim、prompt、狀態列常見的資料夾、git、語言 logo、Powerline 類 glyph。[^4][^2]

這樣分工的好處是：

- emoji 與 icons 各用自己最適合的來源，不會互相污染 glyph 設計。[^5][^1]
- `Symbols Nerd Font Mono` 是 Nerd Fonts 官方提供的「symbols only」單色等寬版本，正好適合拿來當 fallback，而不是取代主字型。[^2][^3]
- 比起自己再做一次「SarasaMonoTCEmojiLite + Nerd Font 全合併」，fallback 架構比較容易更新，也比較不容易踩到寬度、名稱、授權與 patch 衝突問題。[^6][^1]


## 為什麼這樣最穩

SarasaMonoTC-Emoji README 已經明講，VHS 用的是 Headless Chromium + xterm.js，若以錄影穩定性為優先，應選 **Lite**，因為 glyf 單色 outline 在 Chromium/xterm.js 下相容性最好；Color 變體的 CBDT/CBLC 則不夠穩定。[^1]

另一方面，Nerd Font icons 大多是單色 outline glyph，而且很多都在 PUA 區；只要終端機或 renderer 支援字型 fallback，實務上用 `Symbols Nerd Font Mono` 補這層就能正常顯示。[^3][^7]
但要注意，xterm.js 某些 renderer 過去對部分 Nerd Font glyph 有裁切問題，像 DOM renderer 曾出現 glyph cut off 的 issue，所以若你用的是吃 xterm.js 的工具，**WebGL renderer 或較新的 Chromium 環境通常更保險**。[^8]

## 最推薦做法

### 方案 A：字型 fallback，優先推薦

字型順序建議：

1. `SarasaMonoTCEmojiLite`
2. `Symbols Nerd Font Mono`
3. 視需要再補一般 fallback，如 `Noto Sans Mono CJK TC` 或系統 monospace

這是最合理的結構，因為：

- 主體文字與 emoji 都走 `SarasaMonoTCEmojiLite`。[^1]
- Nerd Font icon 只在主字型缺字時才由 `Symbols Nerd Font Mono` 補上。[^3]
- `Symbols Nerd Font Mono` 的定位本來就是「icons only / monospace」補字型用途。[^2]


### 方案 B：直接用某套 patched Nerd Font 當主字型，不推薦作為 VHS 主方案

例如直接改用 `Sarasa Gothic Nerd Font` 類型的 patched font，雖然 icons 會比較省事，但 README 已指出這類方案通常只有 Nerd Font 圖示、沒有完整 emoji，無法解決你要的 VHS 單色 emoji 需求。[^1]

### 方案 C：自己再做二次合併，只有在你要「單檔字型」時才考慮

如果你非常在意某些軟體完全不吃 fallback，才值得考慮把 `SarasaMonoTCEmojiLite` 再 patch 一次 Nerd Font icons。
但這條路的成本比較高，因為你要自己處理：

- PUA mapping 衝突。
- icon 寬度與 advance width。
- Bold / Italic 四個 style 一致性。
- 更新時要跟著 SarasaMonoTC-Emoji 與 Nerd Fonts 雙邊版本跑。[^6][^1]

對你目前的描述，我會先把 **fallback 路線做到穩**，不要一開始就走二次合併。

## 實作建議

### VHS / xterm.js 類工具

若工具本身能指定單一 `font-family` 字串，建議寫成：

```txt
"SarasaMonoTCEmojiLite, Symbols Nerd Font Mono"
```

README 已提供 VHS 基本設定，至少 `Set FontFamily "SarasaMonoTCEmojiLite"` 是官方建議基礎；你可以進一步改成含 fallback 的 font stack，前提是該環境有正確吃 CSS/Chromium font fallback。[^1]

概念上像這樣：

```vhs
Set FontFamily "SarasaMonoTCEmojiLite, Symbols Nerd Font Mono"
Set FontSize 48
Set LetterSpacing 0
Set LineHeight 1.2
```

不過這裡要提醒一點：
VHS 最終是透過 headless browser 渲染，**是否完全吃到多字型 fallback，取決於該環境中的字型安裝與 Chromium 尋字行為**；所以最重要的是先在同一台機器上做實測。[^8][^1]

### 一般終端機

不少終端機已經支援 fallback 或字型鏈設定：

- WezTerm 預設 fallback 甚至已內建 popular Nerd Font Symbols font，代表這類設計本身就是被廣泛採用的做法。[^7]
- 某些編輯器／終端機社群文件也直接建議裝 `Symbols Nerd Font` 或 `Symbols Nerd Font Mono` 作 fallback，而不是一定要用 patched 主字型。[^3]

如果是 Linux / fontconfig 環境，你甚至可以在 fontconfig 裡明確把 Nerd Font symbols 補到 monospace fallback 裡，這樣很多 terminal / GUI app 都會一起受益。[^9]

## 你最該注意的坑

- **不是所有終端機都會完整處理 fallback。** 有些只吃第一個字型，這種環境下 icons 仍可能變方框。[^3]
- **Nerd Font 版本要新。** 社群裡很多「圖示缺字」問題其實是舊版碼位對不上新版 plugin/icon set。[^10][^6]
- **Mono 版本優先。** 你要的是終端機與錄影，不是 GUI 比例字，所以請選 `Symbols Nerd Font Mono`，不要選比例版。[^11][^2]
- **xterm.js renderer 差異要測。** 某些 glyph 在 DOM renderer 可能裁切，但在 WebGL renderer 修正較好。[^8]
- **VHS 首重可重現。** 你的錄影 pipeline 若要穩，請把字型安裝、Chromium 環境、VHS 設定都固定住，不要依賴系統隨機 fallback。[^1]


## 我給你的實務建議

以你的目標來說，最務實的組合是：


| 角色 | 建議字型 | 用途 |
| :-- | :-- | :-- |
| 主字型 | `SarasaMonoTCEmojiLite` | 繁中、英文、單色 emoji、VHS 相容主體。[^1] |
| icon fallback | `Symbols Nerd Font Mono` | Neovim / prompt / terminal UI 的 Nerd Font icons。[^2][^3] |
| 彩色需求備案 | `SarasaMonoTCEmojiCOLRv1` | 只留給已知支援 COLRv1 的 GUI / Chromium 場景，不當 VHS 主力。[^1] |

如果你的目標是「最大相容、最少維護、VHS 可穩定錄影」，這組合目前是最合理的。[^2][^1]

## 下一步

我建議你直接做這三步：

1. 安裝 `SarasaMonoTCEmojiLite` 與 `Symbols Nerd Font Mono`。[^2][^1]
2. 在你常用的終端機與 VHS 設成 `SarasaMonoTCEmojiLite, Symbols Nerd Font Mono`。[^3][^1]
3. 用一份測試字串同時驗證：中文、emoji、Powerline、Nerd Font PUA icons、Neovim 常見圖示。[^12][^1]

 整理一份 **macOS / Linux 的安裝與設定範本**，包含：

- VHS `tape` 設定
- WezTerm / kitty / Ghostty / iTerm2 字型設定
- 一段可直接貼上測試的 icon + emoji 驗證字串
<span style="display:none">[^13][^14][^15][^16][^17]</span>

<div align="center">⁂</div>

[^1]: https://github.com/sspig0127/SarasaMonoTC-Emoji?tab=readme-ov-file

[^2]: https://archlinux.org/packages/extra/any/ttf-nerd-fonts-symbols-mono/

[^3]: https://github.com/zed-industries/zed/discussions/9150

[^4]: https://www.nerdfonts.com

[^5]: https://github.com/ryanoasis/nerd-fonts

[^6]: https://github.com/ryanoasis/nerd-fonts/releases

[^7]: https://wezterm.org/config/fonts.html

[^8]: https://github.com/xtermjs/xterm.js/issues/3807

[^9]: https://dev.to/moniquelive/using-nerd-font-symbols-and-emoji-with-any-unpatched-font-in-linux-3kdo

[^10]: https://www.reddit.com/r/neovim/comments/166ch1a/using_nerd_fonts_but_still_getting_these/

[^11]: https://www.nerdfonts.com/releases

[^12]: https://www.nerdfonts.com/cheat-sheet

[^13]: https://www.nerdfonts.com/font-downloads

[^14]: https://github.com/wezterm/wezterm/issues/3349

[^15]: https://stackoverflow.com/questions/62333627/using-private-use-area-characters-with-reactjs

[^16]: https://www.reddit.com/r/archlinux/comments/11t24on/i_have_nerdfonts_installed_but_still_some/

[^17]: https://gitee.com/bearxup/nerd-fonts

