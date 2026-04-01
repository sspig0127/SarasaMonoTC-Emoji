# SarasaMonoTC-Emoji — Claude Code Context

Python/fonttools 自動化字體建構工具，將 emoji 嵌入 Sarasa Mono TC，產出三種變體：`Color`、`Lite`、`COLRv1`。

## 長期記憶索引

- 主線：`v2.0` sequence emoji（ZWJ / 膚色 / 旗幟）
- Release workflow 目前只剩 `astral-sh/setup-uv@v4` 會觸發 Node.js 20 warning；細節看 `docs/current-focus.md`
- 新對話先看：`CLAUDE.md`、`docs/current-focus.md`、`docs/v2-sequence-implementation.md`
- 歷史脈絡看：`docs/roadmap-history.md`、`.github/colrv1-dev-notes.md`
- 過往 release / commit / push、暫時性 zip/png、COLRv1 排錯過程都不要硬塞進對話上下文

## 必讀檔案

- `build.py`：主建構入口
- `config.yaml`：字體名稱、版本、路徑、priority / force 清單
- `src/emoji_merge.py`：三種變體的 merge 邏輯
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
- `emoji.force_color_codepoints` 與 `colrv1.force_colrv1_codepoints` 要保持同步
- Color forced BMP rename 仍需維持 `post` format 2.0
- 平行建構失敗時要清 partial output
- `detect_font_widths()` 依賴實際字寬，不要硬編碼 500 / 1000

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
