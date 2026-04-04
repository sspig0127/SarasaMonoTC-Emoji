#!/usr/bin/env python3
"""COLRv1 Budget Expansion Analysis

實際情況：現行預算已 100% 用盡（7913 greedy + 223 sequence = 8136/8136）。
任何擴增都需先提高 max_new_glyphs。

模擬前提：max_new_glyphs 從 8136 提高至 PROPOSED_MAX（預設 8450），
額外釋放 314 slots，分析兩種用法：

  方向一：skip-and-continue greedy
    以 314 extra slots 跑 skip-and-continue，最大化單碼 emoji 數量。

  方向二：低成本 sequence 候選
    component emoji 都已選入者，sequence 只需 1 slot。
    從 314 extra slots 中撥出若干給新 sequence。

Usage:
    uv run python scripts/colrv1_budget_analysis.py [--proposed-max N]
"""

import argparse
import json
import sys
import unicodedata
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fontTools.ttLib import TTFont  # noqa: E402

from src.emoji_merge import (  # noqa: E402
    _collect_colrv1_paint_glyph_deps,
    get_emoji_cmap,
    extract_emoji_sequences,
)

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
CURRENT_MAX = 8136          # 現行 max_new_glyphs
PROPOSED_MAX = 8450         # 建議值（safe: 65535 − 56905 − 180 buffer）
RESERVED_SEQ = 223          # priority_sequences 已保留（從 build log 量測）
CURRENT_GREEDY_COST = 7913  # 現行 greedy 單碼消耗（從 JSON）
CURRENT_SEQ_COST = 223      # 現行 sequence 消耗（= RESERVED_SEQ，從 build log）

COLRV1_FONT = PROJECT_ROOT / "fonts" / "Noto-COLRv1.ttf"
SARASA_FONT  = PROJECT_ROOT / "fonts" / "SarasaMonoTC-Regular.ttf"
CURRENT_LIST = PROJECT_ROOT / "docs" / "colrv1-emoji-list.json"
OUTPUT_HTML  = PROJECT_ROOT / "scripts" / "colrv1_budget_report.html"

# ---------------------------------------------------------------------------
# Unicode emoji block 分類
# ---------------------------------------------------------------------------
CATEGORIES: list[tuple[str, list[tuple[int, int]]]] = [
    ("Smileys & Emotion", [(0x1F600, 0x1F64F)]),
    ("People & Body",     [(0x1F440, 0x1F4FF), (0x1F90C, 0x1F9FF)]),
    ("Animals & Nature",  [(0x1F400, 0x1F43F), (0x1F980, 0x1F9BF)]),
    ("Food & Drink",      [(0x1F32D, 0x1F37F), (0x1F950, 0x1F97F)]),
    ("Travel & Places",   [(0x1F300, 0x1F32C), (0x1F680, 0x1F6FF)]),
    ("Activities",        [(0x1F3A0, 0x1F3FF), (0x26BD, 0x26BE), (0x1FA70, 0x1FAFF)]),
    ("Objects",           [(0x1F484, 0x1F4FF), (0x1F527, 0x1F5FF)]),
    ("Symbols",           [(0x1F500, 0x1F52F), (0x2600, 0x27FF)]),
    ("Time / Clock",      [(0x1F550, 0x1F567)]),
]

def categorize(cp: int) -> str:
    for label, ranges in CATEGORIES:
        for lo, hi in ranges:
            if lo <= cp <= hi:
                return label
    return "Other"

def emoji_name(cp: int) -> str:
    try:
        return unicodedata.name(chr(cp), "UNKNOWN")
    except (ValueError, OverflowError):
        return "UNKNOWN"

# ---------------------------------------------------------------------------
# Load current selection
# ---------------------------------------------------------------------------
def load_current(path: Path) -> tuple[set[int], set[str]]:
    with open(path) as f:
        data = json.load(f)
    selected_cp = {int(e["codepoint"].replace("U+", ""), 16) for e in data["emoji"]}
    selected_gn = {e["glyph_name"] for e in data["emoji"]}
    return selected_cp, selected_gn

# ---------------------------------------------------------------------------
# Direction 1 — skip-and-continue with extra budget
# ---------------------------------------------------------------------------
def simulate_skip_and_continue(
    emoji_font: TTFont,
    full_cmap: dict[int, str],
    sarasa_cmap: set[int],
    selected_cp: set[int],
    selected_gn: set[str],
    extra_budget: int,
) -> list[dict]:
    """Emoji that would be added if greedy continues with extra_budget slots."""

    # Pre-warm COLR decompilation
    colr = emoji_font["COLR"].table
    if hasattr(colr, "BaseGlyphList") and colr.BaseGlyphList:
        _ = colr.BaseGlyphList.BaseGlyphPaintRecord

    # Deps already accumulated by current selection
    print("  計算已選 emoji 的 geometry deps（batch）...")
    accumulated = _collect_colrv1_paint_glyph_deps(emoji_font, selected_gn)

    # Candidates: in COLRv1, not skip_existing, not yet selected
    candidates = {
        cp: name
        for cp, name in full_cmap.items()
        if cp not in selected_cp and cp not in sarasa_cmap
    }
    print(f"  候選（未選入）：{len(candidates)} 個")

    added: list[dict] = []
    total_cost = 0

    for cp in sorted(candidates):
        if total_cost >= extra_budget:
            break
        name = candidates[cp]
        deps = _collect_colrv1_paint_glyph_deps(emoji_font, {name})
        deps.discard(name)
        new_deps = deps - accumulated - selected_gn
        cost = 1 + len(new_deps)

        if total_cost + cost > extra_budget:
            continue  # skip（不 break）

        accumulated.update(new_deps)
        total_cost += cost
        added.append({
            "cp": cp,
            "char": chr(cp),
            "unicode_name": emoji_name(cp),
            "cost": cost,
            "category": categorize(cp),
        })

    print(f"  方向一新增：{len(added)} 個（消耗 {total_cost}/{extra_budget} extra slots）")
    return added

# ---------------------------------------------------------------------------
# Direction 2 — cheap sequence candidates
# ---------------------------------------------------------------------------
def find_cheap_sequences(
    emoji_font: TTFont,
    sequences: dict[tuple[int, ...], str],
    selected_cp: set[int],
    selected_gn: set[str],
) -> list[dict]:
    """Sequences where all component emoji are already selected."""
    colr = emoji_font["COLR"].table
    if hasattr(colr, "BaseGlyphList") and colr.BaseGlyphList:
        _ = colr.BaseGlyphList.BaseGlyphPaintRecord

    accumulated = _collect_colrv1_paint_glyph_deps(emoji_font, selected_gn)

    ZWJ      = 0x200D
    SKIN     = {0x1F3FB, 0x1F3FC, 0x1F3FD, 0x1F3FE, 0x1F3FF}
    VS16     = 0xFE0F
    RI_START = 0x1F1E6
    RI_END   = 0x1F1FF

    cheap: list[dict] = []
    for codepoints, glyph_name in sequences.items():
        visible = [cp for cp in codepoints if cp not in (ZWJ, VS16)]
        base_cps = [cp for cp in visible if cp not in SKIN]

        # Skip flag sequences (RI pairs) — Lite 已全域覆蓋，COLRv1 另計
        if all(RI_START <= cp <= RI_END for cp in visible):
            continue

        if not all(cp in selected_cp for cp in base_cps):
            continue

        deps = _collect_colrv1_paint_glyph_deps(emoji_font, {glyph_name})
        deps.discard(glyph_name)
        new_deps = deps - accumulated - selected_gn
        cost = 1 + len(new_deps)

        skin = [cp for cp in visible if cp in SKIN]
        kind = "膚色變體" if skin else "ZWJ 序列"

        seq_str = "".join(chr(cp) for cp in codepoints if cp not in (ZWJ, VS16))
        seq_hex = " ".join(f"U+{cp:04X}" for cp in codepoints)

        cheap.append({
            "codepoints": codepoints,
            "seq_str": seq_str,
            "seq_hex": seq_hex,
            "glyph_name": glyph_name,
            "cost": cost,
            "kind": kind,
        })

    cheap.sort(key=lambda x: (x["cost"], x["codepoints"]))
    return cheap

# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------
HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<title>COLRv1 Budget Expansion Analysis</title>
<style>
  body {{ font-family: sans-serif; margin: 20px; background: #1e1e1e; color: #d4d4d4; }}
  h1 {{ color: #569cd6; }}
  h2 {{ color: #4ec9b0; border-bottom: 1px solid #444; padding-bottom: 6px; }}
  h3 {{ color: #dcdcaa; }}
  .summary {{ background: #252526; padding: 14px; border-radius: 6px; margin: 12px 0; line-height: 1.8; }}
  .budget-bar {{ background:#333; border-radius:4px; height:18px; margin:6px 0; position:relative; }}
  .budget-fill {{ background:#569cd6; border-radius:4px 0 0 4px; height:100%; }}
  .budget-extra {{ background:#4ec9b0; height:100%; }}
  .emoji-grid {{ display:flex; flex-wrap:wrap; gap:6px; margin:10px 0; }}
  .ec {{ display:inline-flex; flex-direction:column; align-items:center;
         background:#2d2d2d; border-radius:4px; padding:6px 8px; min-width:60px; }}
  .ec .glyph {{ font-size:2em; line-height:1.2; font-family:'SMTCE-COLRv1',monospace; }}
  .ec .info {{ font-size:0.6em; color:#888; text-align:center; max-width:80px; }}
  .cost1  {{ border:1px solid #4ec9b0; }}
  .cost-mid {{ border:1px solid #dcdcaa; }}
  .cost-hi  {{ border:1px solid #f44747; }}
  .category-group {{ margin:16px 0; }}
  .ec-wrap {{ display:inline-flex; flex-direction:column; align-items:center; max-width:120px; }}
  .rel-row {{ font-size:0.72em; color:#aaa; margin-top:3px; text-align:center; line-height:1.6; }}
  .rel-chip {{ font-family:'SMTCE-COLRv1',monospace; font-size:1.3em; cursor:default; margin:0 1px; }}
  .rel-new  {{ font-family:'SMTCE-COLRv1',monospace; font-size:1.3em; cursor:default;
               margin:0 1px; color:#4ec9b0; }}
  .no-rel   {{ color:#555; font-style:italic; }}
  table {{ border-collapse:collapse; width:100%; margin:10px 0; font-size:0.9em; }}
  th, td {{ border:1px solid #444; padding:6px 10px; text-align:left; }}
  th {{ background:#2d2d2d; color:#569cd6; }}
  .seq-char {{ font-family:'SMTCE-COLRv1',monospace; font-size:1.8em; }}
  .tag {{ display:inline-block; padding:2px 6px; border-radius:3px; font-size:0.8em; }}
  .tag-skin {{ background:#4e3a2d; color:#dcdcaa; }}
  .tag-zwj  {{ background:#1e3a4e; color:#9cdcfe; }}
  small {{ color:#888; }}
  .note {{ background:#2a2a1e; border-left:3px solid #dcdcaa;
           padding:8px 12px; margin:8px 0; font-size:0.88em; }}
</style>
<script>
async function loadFont() {{
  const p = '../output/fonts-colrv1/SarasaMonoTC-Emoji-COLRv1-Regular.ttf';
  try {{
    const f = new FontFace('SMTCE-COLRv1', `url(${{p}})`);
    await f.load();
    document.fonts.add(f);
    document.getElementById('fs').textContent = '✅ COLRv1 字體已載入（現行版本，方向一新增項目無法顯示）';
  }} catch(e) {{
    document.getElementById('fs').textContent =
      '⚠️ 字體未載入 → 先執行：uv run python build.py --colrv1 --styles Regular';
  }}
}}
window.onload = loadFont;
</script>
</head>
<body>
<h1>COLRv1 Budget Expansion Analysis</h1>
<p id="fs">🔄 載入字體...</p>

<div class="summary">
  <strong>現狀</strong>：8,136 / 8,136 slots 已用盡（greedy 7,913 + sequence 223）<br>
  <strong>前提</strong>：max_new_glyphs 提高至 {proposed_max}（+{extra_budget} slots）<br>
  <br>
  <strong>方向一</strong>（skip-and-continue greedy）模擬可新增：<strong>{dir1_count} 個 emoji 候選</strong><br>
  <strong>方向二</strong>（低成本 sequence）：共 {dir2_count} 筆候選，cost=1 共 {dir2_cost1} 筆；
  扣除方向一後剩餘 {dir2_budget} slots，可納入 <strong>{dir2_fits} 個 sequence</strong><br>
  <br>
  <em>方向一與方向二共用 {extra_budget} extra slots。使用 <code>--dir1-slots N --dir2-max-cost M</code> 調整情境。</em>
</div>

<div class="note">
  💡 建議實作路線：先實作方向一（改 1 行程式碼 + 提高 max_new_glyphs），
  再從方向二篩選高價值 sequence 加入 priority_sequences（佔用部分 extra budget）。
</div>

<h2>方向一：skip-and-continue 可新增的單碼 emoji</h2>
<p>以現行 greedy 截止點以後的候選，在 +{extra_budget} slots 內 skip-and-continue 可加入的 emoji。<br>
顏色：<span style="color:#4ec9b0">綠框=cost 1</span>、
<span style="color:#dcdcaa">黃框=cost 2–5</span>、
<span style="color:#f44747">紅框=cost 6+</span></p>
{dir1_html}

<h2>方向二：低成本 sequence 候選（所有 component 已選入）</h2>
<p>以下 sequence 的 base emoji 已在選單中；cost=1 表示不帶新 dep，最便宜。<br>
視覺上 COLRv1 字體目前尚未包含這些 sequence，顯示可能為 fallback 字體。</p>
{dir2_html}

</body>
</html>
"""

_STOP_WORDS = {
    # 介詞 / 連接詞
    "WITH", "AND", "OF", "THE", "IN", "ON", "AT", "TO", "FOR", "A", "AN",
    # 顏色（避免 GREEN BOOK 靠顏色而非 BOOK 匹配）
    "RED", "ORANGE", "YELLOW", "GREEN", "BLUE", "PURPLE", "VIOLET",
    "PINK", "BROWN", "GREY", "GRAY", "CYAN", "MAGENTA",
    "WHITE", "BLACK",
    # 通用形容詞
    "LIGHT", "DARK", "HEAVY", "SMALL", "LARGE", "MEDIUM",
    "OPEN", "CLOSED", "NEW", "OLD", "FIRST", "LAST",
    # 字體 / 符號用詞
    "SIGN", "MARK", "SYMBOL", "BUTTON", "LATIN", "CAPITAL",
    # 方向
    "LEFT", "RIGHT", "UP", "DOWN",
    # 數字詞（避免 TWO OCLOCK 誤配 TWO HEARTS / TWO MEN HOLDING HANDS）
    "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX",
    "SEVEN", "EIGHT", "NINE", "TEN", "ELEVEN", "TWELVE",
    # 其他高頻但低資訊詞
    "FACE", "EMOJI",
}

def _keywords(name: str) -> set[str]:
    return {w for w in name.upper().split() if w not in _STOP_WORDS and len(w) > 2}

def build_selected_index(selected_cp: set[int], full_cmap: dict[int, str]) -> list[dict]:
    """Build list of currently selected single-codepoint emoji with names.

    Uses unicodedata.name() for ALL selected codepoints so BMP force-codepoints
    and other emoji not in full_cmap are still included as related candidates.
    """
    result = []
    for cp in sorted(selected_cp):
        try:
            char = chr(cp)
            name = unicodedata.name(char, "")
        except (ValueError, OverflowError):
            continue
        if name:
            result.append({"cp": cp, "char": char, "unicode_name": name,
                            "keywords": _keywords(name)})
    # Debug: show index size
    return result

def find_related(new_name: str, selected_index: list[dict], max_results: int = 6) -> list[dict]:
    """Find currently-selected emoji with overlapping name keywords."""
    kw = _keywords(new_name)
    if not kw:
        return []
    scored = []
    for e in selected_index:
        overlap = len(kw & e["keywords"])
        if overlap > 0:
            scored.append((overlap, e))
    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:max_results]]


def cost_class(cost: int) -> str:
    if cost <= 1: return "cost1"
    if cost <= 5: return "cost-mid"
    return "cost-hi"

def build_dir1_html(added: list[dict], selected_index: list[dict]) -> str:
    if not added:
        return "<p>無新增（extra budget 不足或全為高成本 emoji）</p>"

    # Build an index of Direction 1 additions themselves for cross-reference
    dir1_index = [
        {"cp": e["cp"], "char": e["char"], "unicode_name": e["unicode_name"],
         "keywords": _keywords(e["unicode_name"])}
        for e in added
    ]

    from collections import defaultdict
    by_cat: dict[str, list] = defaultdict(list)
    for e in added:
        by_cat[e["category"]].append(e)
    parts = []
    for cat, items in sorted(by_cat.items()):
        parts.append(
            f'<div class="category-group"><h3>{cat} ({len(items)})</h3>'
            '<div class="emoji-grid">'
        )
        for e in sorted(items, key=lambda x: x["cp"]):
            cls = cost_class(e["cost"])
            short = e["unicode_name"][:28]

            # Related in current selection
            related = find_related(e["unicode_name"], selected_index)
            # Related in Direction 1 itself (exclude self)
            dir1_related = [r for r in find_related(e["unicode_name"], dir1_index)
                            if r["cp"] != e["cp"]]

            rel_parts = []
            if related:
                chips = "".join(
                    '<span title="{}" class="rel-chip">{}</span>'.format(
                        r["unicode_name"], r["char"])
                    for r in related
                )
                rel_parts.append(f'已選相關：{chips}')
            if dir1_related:
                chips = "".join(
                    '<span title="{}" class="rel-chip rel-new">{}</span>'.format(
                        r["unicode_name"], r["char"])
                    for r in dir1_related
                )
                rel_parts.append(f'同批新增：{chips}')
            if not related and not dir1_related:
                rel_parts.append('<span class="no-rel">（現行選單無相關）</span>')

            rel_html = '<div class="rel-row">' + '　'.join(rel_parts) + '</div>'

            parts.append(
                f'<div class="ec-wrap">'
                f'<div class="ec {cls}">'
                f'<span class="glyph">{e["char"]}</span>'
                f'<span class="info">U+{e["cp"]:04X}<br>{short}<br>cost={e["cost"]}</span>'
                f'</div>'
                f'{rel_html}'
                f'</div>'
            )
        parts.append("</div></div>")
    return "\n".join(parts)

def _seq_table(seqs: list[dict], limit: int = 300) -> str:
    if not seqs:
        return "<p><em>（無）</em></p>"
    rows = []
    for s in seqs[:limit]:
        tag = ('<span class="tag tag-skin">膚色</span>' if s["kind"] == "膚色變體"
               else '<span class="tag tag-zwj">ZWJ</span>')
        rows.append(
            f'<tr>'
            f'<td class="seq-char">{s["seq_str"]}</td>'
            f'<td><code>{s["seq_hex"]}</code></td>'
            f'<td>{tag}</td>'
            f'<td>{s["cost"]}</td>'
            f'</tr>'
        )
    out = ('<table><thead><tr><th>Emoji</th><th>Codepoints</th>'
           '<th>類型</th><th>Cost</th></tr></thead><tbody>'
           + "\n".join(rows) + "</tbody></table>")
    if len(seqs) > limit:
        out += f"<small>（共 {len(seqs)} 筆，僅顯示前 {limit}）</small>"
    return out


def build_dir2_html(
    fits: list[dict],
    over: list[dict],
    consumed: int,
    dir2_budget: int,
    dir2_max_cost: int,
) -> str:
    fits_skin = [s for s in fits if s["kind"] == "膚色變體"]
    fits_zwj  = [s for s in fits if s["kind"] == "ZWJ 序列"]
    over_skin = [s for s in over if s["kind"] == "膚色變體"]
    over_zwj  = [s for s in over if s["kind"] == "ZWJ 序列"]

    filter_note = (f"cost ≤ {dir2_max_cost}" if dir2_max_cost < 99 else "不限 cost")
    budget_note = (f"Direction 1 占用後剩餘 {dir2_budget} slots" if dir2_budget < 314
                   else f"全部 {dir2_budget} slots 給方向二")

    html = f"""
<div class="summary">
  篩選條件：{filter_note}　預算：{budget_note}<br>
  <strong>可納入：{len(fits)} 個 sequence（消耗 {consumed}/{dir2_budget} slots，剩餘 {dir2_budget - consumed} slots）</strong><br>
  超出或過濾：{len(over)} 筆
</div>

<h3>✅ 可納入（{len(fits)} 筆）</h3>
<details open><summary>膚色變體 {len(fits_skin)} 筆</summary>{_seq_table(fits_skin)}</details>
<details open><summary>ZWJ 序列 {len(fits_zwj)} 筆</summary>{_seq_table(fits_zwj)}</details>

<h3>❌ 超出預算或高於 cost 門檻（{len(over)} 筆）</h3>
<details><summary>膚色變體 {len(over_skin)} 筆</summary>{_seq_table(over_skin, limit=50)}</details>
<details><summary>ZWJ 序列 {len(over_zwj)} 筆</summary>{_seq_table(over_zwj, limit=50)}</details>
"""
    return html

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--proposed-max", type=int, default=PROPOSED_MAX,
                        help=f"模擬目標 max_new_glyphs（預設 {PROPOSED_MAX}）")
    parser.add_argument("--dir1-slots", type=int, default=0,
                        help="Direction 1 已決定使用的 slots（從 extra budget 扣除）")
    parser.add_argument("--dir2-max-cost", type=int, default=99,
                        help="Direction 2 每個 sequence 的最高 cost 門檻（預設不限）")
    args = parser.parse_args()

    proposed_max  = args.proposed_max
    extra_budget  = proposed_max - CURRENT_MAX
    dir1_slots    = args.dir1_slots
    dir2_max_cost = args.dir2_max_cost
    dir2_budget   = extra_budget - dir1_slots

    print("=== COLRv1 Budget Expansion Analysis ===\n")
    print(f"現行 max_new_glyphs : {CURRENT_MAX}  (已用盡：greedy {CURRENT_GREEDY_COST} + seq {CURRENT_SEQ_COST})")
    print(f"模擬目標           : {proposed_max}  (+{extra_budget} extra slots)")
    if dir1_slots:
        print(f"Direction 1 已耗   : {dir1_slots} slots → Direction 2 可用：{dir2_budget} slots")
    if dir2_max_cost < 99:
        print(f"Direction 2 cost 上限：{dir2_max_cost}")
    print()

    print("[1/5] 讀取現有選單...")
    selected_cp, selected_gn = load_current(CURRENT_LIST)
    print(f"  已選：{len(selected_cp)} emoji")
    # Build after full_cmap is loaded (step 2); placeholder here
    selected_index: list[dict] = []

    print("\n[2/5] 載入字體...")
    emoji_font  = TTFont(str(COLRV1_FONT))
    sarasa_font = TTFont(str(SARASA_FONT))
    sarasa_cmap: set[int] = set(sarasa_font["cmap"].getBestCmap().keys())
    full_cmap   = get_emoji_cmap(emoji_font)
    print(f"  COLRv1 全量 cmap：{len(full_cmap)} emoji")
    print(f"  Sarasa cmap：{len(sarasa_cmap)} codepoints")
    selected_index = build_selected_index(selected_cp, full_cmap)
    print(f"  已選 emoji 索引：{len(selected_index)} 筆")

    print("\n[3/5] 模擬方向一：skip-and-continue greedy...")
    dir1 = simulate_skip_and_continue(
        emoji_font, full_cmap, sarasa_cmap, selected_cp, selected_gn, extra_budget
    )
    cost_dist: dict[int, int] = {}
    for e in dir1:
        cost_dist[e["cost"]] = cost_dist.get(e["cost"], 0) + 1
    print("  成本分布：" + ", ".join(f"cost={k}×{v}" for k, v in sorted(cost_dist.items())))

    print("\n[4/5] 分析方向二：低成本 sequence 候選...")
    sequences = extract_emoji_sequences(emoji_font)
    print(f"  COLRv1 GSUB sequences 總計：{len(sequences)} 筆")
    dir2_all = find_cheap_sequences(emoji_font, sequences, selected_cp, selected_gn)
    dir2_cost1 = sum(1 for s in dir2_all if s["cost"] == 1)
    print(f"  候選（component 已選）：{len(dir2_all)} 筆（cost=1: {dir2_cost1} 筆）")

    # Apply cost filter and budget cap
    dir2_filtered = [s for s in dir2_all if s["cost"] <= dir2_max_cost]
    dir2_fits: list[dict] = []
    dir2_over: list[dict] = []
    consumed = 0
    for s in dir2_filtered:  # already sorted by cost asc
        if consumed + s["cost"] <= dir2_budget:
            dir2_fits.append(s)
            consumed += s["cost"]
        else:
            dir2_over.append(s)
    print(f"  cost≤{dir2_max_cost}，預算 {dir2_budget} slots 內：{len(dir2_fits)} 個 sequence（消耗 {consumed} slots）")
    print(f"  預算內剩餘：{dir2_budget - consumed} slots；超出或過濾：{len(dir2_all) - len(dir2_fits)} 筆")

    print("\n[5/5] 產生 HTML 報表...")
    html = HTML_TEMPLATE.format(
        proposed_max=proposed_max,
        extra_budget=extra_budget,
        dir1_count=len(dir1),
        dir2_count=len(dir2_all),
        dir2_cost1=dir2_cost1,
        dir2_fits=len(dir2_fits),
        dir2_budget=dir2_budget,
        dir1_html=build_dir1_html(dir1, selected_index),
        dir2_html=build_dir2_html(dir2_fits, dir2_over, consumed, dir2_budget, dir2_max_cost),
    )
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print(f"  → {OUTPUT_HTML}\n")
    print("完成。開啟報表：")
    print(f"  open {OUTPUT_HTML}")

if __name__ == "__main__":
    main()
