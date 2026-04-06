# SarasaMonoTC-Emoji — Claude Code Context

Python/fonttools 自動化字體建構工具，將 emoji 嵌入 Sarasa Mono TC，產出四種變體：`Color`、`Lite`、`COLRv1`、`Nerd Lite`。

## 長期記憶索引

- `v2.1` Nerd Lite 第四變體已發佈；折衷方案：Powerline 1 欄，其他集合 2 欄
- `v2.2` COLRv1 budget 擴增：skip-and-continue greedy + 10 priority emoji + 221 sequences（↑ 629 → 811，8,327/8,450 slots）
- `v2.3` Chromium TrueType composite bug 修復：大 offset 複合字形（家庭 emoji 等 29 個）分解為 simple glyph，家庭 emoji 全人物正確渲染
- CBLC name-conflict 技術債已解決：`force_color_codepoints` 擴增至 118 項（含 103 個新增，71 BMP + 32 非 BMP），Color 變體衝突 127 → 24
- 基底字體更新至 Sarasa Gothic v1.0.37；`docs/upstream-versions.json` + `.github/workflows/check-upstream.yml` 已建立月度追蹤
- Release workflow 目前只剩 `astral-sh/setup-uv@v4` 會觸發 Node.js 20 warning；細節看 `docs/current-focus.md`
- 新對話先看：`CLAUDE.md`、`docs/current-focus.md`
- 歷史脈絡看：`docs/roadmap-history.md`、`.github/colrv1-dev-notes.md`
- 過往 release / commit / push、暫時性 zip/png、COLRv1 排錯過程都不要硬塞進對話上下文

## 必讀檔案

- `build.py`：主建構入口
- `config.yaml`：字體名稱、版本、路徑、priority / force 清單
- `src/emoji_merge.py`：四種變體的 merge 邏輯
- `src/config.py`：`FontConfig` 驗證
- `tests/test_emoji_merge.py`、`tests/test_font_output.py`：核心回歸測試

## 需要時再讀

- `.github/copilot-instructions.md`：完整專案規範與 CI/CD
- `.github/colrv1-dev-notes.md`：COLRv1 / UPM / glyph budget debug
- `ROADMAP.md`：版本狀態與發佈方向
- `docs/roadmap-history.md`：舊版本技術決策
- `docs/v2-sequence-implementation.md`：sequence emoji 設計紀錄
- `verify-emoji.html`：本地視覺驗證

## Source Of Truth

- 字體名稱、版本、輸出路徑、priority 清單、force 清單只改 `config.yaml`
- 不要在 Python 程式碼 hardcode family name、output dir、codepoint 清單
- `docs/colrv1-emoji-list.json` 是 `build.py --colrv1` 產物，不手改

## 關鍵規則

- `emoji_width_multiplier` 預設 `2`
- `skip_existing: true` 預設保留 Sarasa 原有字形
- **Lite 旗幟**：所有標準 RI-pair 旗幟全域套用 2-column 自訂旗面設計，無白名單；不需要在 `config.yaml` 設定 `custom_flag_sequences`
- **COLRv1 旗幟**：受 glyph budget 限制，透過 `colrv1.priority_sequences` 控制優先引入的旗幟
- `emoji.force_color_codepoints` 與 `colrv1.force_colrv1_codepoints` 要保持同步
- Color forced BMP rename 仍需維持 `post` format 2.0
- 平行建構失敗時要清 partial output
- `detect_font_widths()` 依賴實際字寬，不要硬編碼 500 / 1000
- **Nerd Lite PUA merge**：Powerline（E0A0–E0D7）1 欄（scale=500/2048），其他集合 2 欄（scale=1000/2048）；`single_column_ranges` 在 `config.yaml` 控制
- Nerd Fonts Mono UPM=2048，1 cell = 1 em = 2048 units；scale 公式：`target_advance / nerd_upm`

## COLRv1 只記住這些

- Noto-COLRv1 `UPM=1024`，Sarasa `UPM=1000`
- paint tree 的 font-unit 座標也要跟著縮放
- helper glyph metrics 不能清成 `(0, 0)`
- 高位移樣本：`🟡` / `🟢`

## 工作流程

1. 看 `git status`
2. 讀 `CLAUDE.md`、`config.yaml`、相關核心檔
3. COLRv1 問題再補看 `.github/colrv1-dev-notes.md`
4. 改完先跑最小必要測試
5. 視覺問題用 `verify-emoji.html`
6. 更新版本或行為時，補 `ROADMAP.md` / 相關文件
