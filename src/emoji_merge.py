"""Core emoji merging logic for SarasaMonoTC-Emoji.

Strategy:
  - SarasaMonoTC is the base font (already has full CJK support)
  - NotoColorEmoji provides CBDT/CBLC color bitmap emoji
  - We detect Sarasa's widths at runtime (no hardcoded UPM assumptions)
  - Only single-codepoint emoji are handled (no ZWJ sequences in v1)
  - CBDT/CBLC tables are deep-copied; fonttools recompiles with correct
    glyph IDs based on the merged font's glyph order

Background research:
  - No existing open-source project merges color emoji into SarasaMonoTC
  - thedemons/merge_color_emoji_font (70★) only documents a FontLab GUI approach
  - This is the first known Python/fonttools automated implementation
"""

import copy
from collections import Counter
from typing import Optional

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import _c_m_a_p as cmap_module
from fontTools.ttLib.tables._g_l_y_f import Glyph as TTGlyph

from .config import FontConfig

# Codepoint ranges to skip when extracting emoji
# These are either already handled by Sarasa or are not user-visible emoji
_SKIP_CODEPOINT_RANGES = [
    (0x0000, 0x00FF),    # ASCII + Latin-1 Supplement
    (0xFE00, 0xFE0F),    # Variation Selectors
    (0xE0100, 0xE01EF),  # Variation Selectors Supplement
]


def get_emoji_cmap(emoji_font: TTFont) -> dict[int, str]:
    """Extract single-codepoint emoji mappings from NotoColorEmoji.

    getBestCmap() returns only direct codepoint→glyph mappings.
    ZWJ sequences are handled via GSUB ligatures and do not appear here,
    so this naturally filters to single-codepoint emoji only.

    Args:
        emoji_font: TTFont object for NotoColorEmoji

    Returns:
        Dict mapping codepoint -> glyph_name for emoji to merge
    """
    raw = emoji_font["cmap"].getBestCmap() or {}
    result = {}
    for cp, name in raw.items():
        if any(s <= cp <= e for s, e in _SKIP_CODEPOINT_RANGES):
            continue
        result[cp] = name
    return result


def detect_font_widths(base_font: TTFont) -> tuple[int, int]:
    """Detect half-width and full-width from the base font at runtime.

    Sarasa Mono TC maintains a strict 2:1 ratio between Latin (half-width)
    and CJK (full-width) characters. We detect these widths by sampling
    known codepoints rather than hardcoding UPM-specific values.

    Args:
        base_font: TTFont object for SarasaMonoTC

    Returns:
        Tuple of (half_width, full_width) in font units

    Raises:
        ValueError: If a 2:1 ratio cannot be detected
    """
    cmap = base_font["cmap"].getBestCmap() or {}
    hmtx = base_font["hmtx"]

    half_width: Optional[int] = None
    full_width: Optional[int] = None

    # Sample ASCII 'A' for half-width
    if 0x0041 in cmap:
        half_width, _ = hmtx[cmap[0x0041]]

    # Sample CJK '一' for full-width
    if 0x4E00 in cmap:
        full_width, _ = hmtx[cmap[0x4E00]]

    if half_width and full_width and full_width == 2 * half_width:
        return half_width, full_width

    # Fallback: scan hmtx for the most common 2:1 width pair
    widths = Counter(w for w, _ in hmtx.metrics.values() if w > 0)
    for w, _ in widths.most_common(20):
        if w * 2 in widths:
            return w, w * 2

    top = widths.most_common(5)
    raise ValueError(
        f"Cannot detect 2:1 width ratio from font. "
        f"Top widths (width, count): {top}"
    )


def _strip_mac_name_records(font: TTFont) -> None:
    """Remove all Mac platform (platformID=1) name records.

    Sarasa's original Mac name records contain CJK characters encoded as
    mac_roman, which fonttools cannot re-encode when saving. Since modern
    systems (macOS 10.5+, Windows, Linux) use Windows Unicode platform
    records (platformID=3), removing platformID=1 records is safe.
    """
    name_table = font["name"]
    before = len(name_table.names)
    name_table.names = [r for r in name_table.names if r.platformID != 1]
    removed = before - len(name_table.names)
    if removed:
        print(f"  Stripped {removed} Mac platform name records (mac_roman incompatible)")


def _update_cmap(
    base_font: TTFont,
    emoji_cmap: dict[int, str],
    added_set: set[str],
) -> int:
    """Add emoji codepoints to font's cmap tables.

    Creates a Windows Unicode format=12 table if not present (required for
    supplementary codepoints > U+FFFF). Also updates format=4 for BMP emoji.

    Returns:
        Number of new codepoint entries added
    """
    # Find existing tables
    fmt12_win: Optional[object] = None
    fmt4_win: Optional[object] = None
    fmt12_uni: Optional[object] = None

    for table in base_font["cmap"].tables:
        if table.platformID == 3:
            if table.platEncID == 10 and table.format == 12:
                fmt12_win = table
            elif table.platEncID == 1 and table.format == 4:
                fmt4_win = table
        elif table.platformID == 0 and table.format == 12:
            fmt12_uni = table

    # Create Windows format=12 table if missing (needed for emoji > U+FFFF)
    if fmt12_win is None:
        fmt12_win = cmap_module.cmap_format_12(12)
        fmt12_win.platEncID = 10
        fmt12_win.platformID = 3
        fmt12_win.language = 0
        fmt12_win.cmap = {}
        # Seed with existing BMP entries so existing glyphs are not lost
        if fmt4_win:
            fmt12_win.cmap.update(fmt4_win.cmap)
        base_font["cmap"].tables.append(fmt12_win)
        print("  Created new Windows format=12 cmap table")

    added = 0
    for cp, name in emoji_cmap.items():
        if name not in added_set:
            continue

        # format=12 handles all Unicode planes (BMP + supplementary)
        if cp not in fmt12_win.cmap:
            fmt12_win.cmap[cp] = name
            added += 1

        # Also add BMP emoji to format=4 table for legacy compatibility
        if fmt4_win and cp <= 0xFFFF and cp not in fmt4_win.cmap:
            fmt4_win.cmap[cp] = name

        # Mirror to Unicode platform format=12 if present
        if fmt12_uni and cp not in fmt12_uni.cmap:
            fmt12_uni.cmap[cp] = name

    return added


def _filter_cblc_to_added_glyphs(
    base_font: TTFont,
    emoji_glyphs_to_add: list[str],
) -> None:
    """Filter CBLC IndexSubTables to only include glyphs we newly added.

    Problem: CBLC (deep-copied from NotoColorEmoji) may reference 'conflicting'
    glyph names that already existed in Sarasa at low glyph IDs. Those low IDs
    interleave with our high-ID new glyphs, breaking the strictly-increasing
    requirement. Fonttools raises AssertionError when compiling CBLC.

    Fix: remove from each IndexSubTable any glyph whose Sarasa ID is NOT
    in the newly-added range. The conflicting glyphs still exist in Sarasa
    (rendered by Sarasa's own glyph outlines) — they just lose their color
    bitmap override, which is acceptable.

    This must be called AFTER setGlyphOrder() so getGlyphID() works correctly.
    """
    if "CBLC" not in base_font:
        return

    valid_names = set(emoji_glyphs_to_add)
    cblc = base_font["CBLC"]
    removed_total = 0

    for strike in cblc.strikes:
        for sub in strike.indexSubTables:
            original_len = len(sub.names)
            valid_idx = [i for i, n in enumerate(sub.names) if n in valid_names]

            if len(valid_idx) == original_len:
                continue

            sub.names = [sub.names[i] for i in valid_idx]

            # locations is a parallel list (verified by fonttools toXML source):
            # zip(self.names, self.locations) is used when serializing
            if (
                hasattr(sub, "locations")
                and isinstance(sub.locations, list)
                and len(sub.locations) == original_len
            ):
                sub.locations = [sub.locations[i] for i in valid_idx]

            removed_total += original_len - len(valid_idx)

        # Drop empty sub-tables
        strike.indexSubTables = [s for s in strike.indexSubTables if s.names]

    # Drop empty strikes
    cblc.strikes = [s for s in cblc.strikes if s.indexSubTables]
    if hasattr(cblc, "numSizes"):
        cblc.numSizes = len(cblc.strikes)

    if removed_total:
        print(f"  Filtered {removed_total} conflicting entries from CBLC IndexSubTables")


def _force_decompile_cbdt(emoji_font: TTFont) -> None:
    """Force full decompilation of CBDT/CBLC before deep copy.

    fonttools uses lazy loading; we must trigger decompilation before
    deep copying to ensure all data is in Python objects (not raw bytes).
    """
    if "CBLC" in emoji_font:
        strikes = emoji_font["CBLC"].strikes
        for strike in strikes:
            for sub in strike.indexSubTables:
                _ = sub.names  # trigger name list decompile

    if "CBDT" in emoji_font:
        strike_data = emoji_font["CBDT"].strikeData
        for strike_dict in strike_data:
            if isinstance(strike_dict, dict):
                for glyph_data in strike_dict.values():
                    if hasattr(glyph_data, "data"):
                        _ = glyph_data.data  # trigger bitmap decompile


def merge_emoji(
    base_font_path: str,
    emoji_font_path: str,
    config: FontConfig,
) -> TTFont:
    """Merge NotoColorEmoji CBDT/CBLC color emoji into SarasaMonoTC.

    Steps:
    1. Load fonts, detect Sarasa's half/full width at runtime
    2. Extract emoji cmap (single codepoints only)
    3. Filter out codepoints already in Sarasa (preserve existing glyphs)
    4. Deep-copy CBDT/CBLC tables into Sarasa
       (fonttools recompiles with correct glyph IDs on save)
    5. Append emoji glyph names to glyph order (contiguous block at end)
    6. Add empty glyph placeholders in glyf table
    7. Set emoji advance width in hmtx (= full_width, i.e. 2x half-width)
    8. Update cmap with emoji codepoints
    9. Update maxp, hhea, OS/2

    Args:
        base_font_path: Path to SarasaMonoTC-{Style}.ttf
        emoji_font_path: Path to NotoColorEmoji.ttf
        config: FontConfig object

    Returns:
        Merged TTFont object (caller must call .save() and .close())
    """
    print(f"  Loading base font: {base_font_path}")
    # lazy=True, recalcBBoxes=False: Glyph.compile() returns raw bytes for existing
    # glyphs when recalcBBoxes=False, instead of decompiling+recompiling them.
    # Without this, fonttools changes flag encoding (e.g. REPEAT→literal) which
    # OTS 9.2.0 rejects with "Bad glyph flag, bit 6 must be set to zero".
    base_font = TTFont(base_font_path, lazy=True, recalcBBoxes=False)
    print(f"  Loading emoji font: {emoji_font_path}")
    emoji_font = TTFont(emoji_font_path)

    # Step 1: detect widths
    half_width, full_width = detect_font_widths(base_font)
    emoji_width = half_width * config.emoji_width_multiplier
    print(f"  Detected widths — half: {half_width}, full: {full_width}, emoji: {emoji_width}")

    # Step 2: extract emoji cmap
    emoji_cmap = get_emoji_cmap(emoji_font)
    print(f"  Emoji cmap entries: {len(emoji_cmap)}")

    # Step 3: filter existing codepoints
    if config.skip_existing:
        base_cmap = base_font["cmap"].getBestCmap() or {}
        before = len(emoji_cmap)
        emoji_cmap = {cp: name for cp, name in emoji_cmap.items() if cp not in base_cmap}
        print(f"  Filtered existing codepoints: {before} → {len(emoji_cmap)}")

    if not emoji_cmap:
        print("  No new emoji to add.")
        emoji_font.close()
        return base_font

    # Build emoji_glyphs_to_add in NotoColorEmoji's GLYPH ID ORDER (not codepoint order).
    #
    # Critical: CBLC's IndexSubTable requires glyph IDs to be strictly increasing.
    # If we add glyphs sorted by codepoint, but CBLC references them in NotoColorEmoji's
    # internal glyph order (which may differ), the Sarasa glyph IDs won't be monotonic
    # and fonttools will raise AssertionError on compile.
    #
    # Solution: add ALL NotoColorEmoji glyphs (not just the cmap-filtered set) in
    # NotoColorEmoji's glyph order, excluding only name conflicts with Sarasa.
    # Glyphs not in emoji_cmap become "orphan" glyphs (in font but no cmap entry),
    # which is harmless and required for CBLC table integrity.
    base_existing_names = set(base_font.getGlyphOrder())
    emoji_all_glyph_order = emoji_font.getGlyphOrder()

    emoji_glyphs_to_add = [
        name for name in emoji_all_glyph_order
        if name not in base_existing_names
    ]

    name_conflicts = len(emoji_all_glyph_order) - len(emoji_glyphs_to_add)
    print(f"  NotoColorEmoji total: {len(emoji_all_glyph_order)} glyphs "
          f"(name conflicts with Sarasa: {name_conflicts})")
    print(f"  Glyphs to add (in NotoColorEmoji glyph order): {len(emoji_glyphs_to_add)}")

    # Step 4: deep-copy CBDT/CBLC tables
    has_cbdt = "CBDT" in emoji_font and "CBLC" in emoji_font
    if has_cbdt:
        print("  Copying CBDT/CBLC tables...")
        _force_decompile_cbdt(emoji_font)
        base_font["CBDT"] = copy.deepcopy(emoji_font["CBDT"])
        base_font["CBLC"] = copy.deepcopy(emoji_font["CBLC"])
    else:
        print("  Warning: emoji font has no CBDT/CBLC tables — only outline glyphs will be added")

    # Step 5: append emoji glyph names to glyph order (contiguous at end)
    # NOTE: do NOT update maxp.numGlyphs here — wait until glyf is populated
    # to avoid "corrupt loca table" warnings from fonttools internal checks
    original_order = base_font.getGlyphOrder()
    new_order = original_order + emoji_glyphs_to_add

    # IMPORTANT: access glyf BEFORE setGlyphOrder so decompile uses the original
    # glyph count (matching loca). If we call setGlyphOrder first, fonttools sees
    # 60767 names but loca only has ~56887 entries; the mismatch causes fonttools
    # to recompile Sarasa's existing glyphs from Python objects instead of raw bytes,
    # changing the flag encoding (e.g. REPEAT→literal) which OTS 9.2.0 rejects.
    if "glyf" in base_font:
        base_glyf = base_font["glyf"]  # triggers decompile with original glyph order

    base_font.setGlyphOrder(new_order)

    # Filter CBLC to only include newly-added glyphs.
    # 146 name-conflicting glyphs (e.g. .notdef) exist in both Sarasa and NotoColorEmoji
    # at low Sarasa IDs — interleaved with our high-ID new glyphs, they break the
    # strictly-increasing glyph ID requirement in CBLC IndexSubTables.
    if has_cbdt:
        _filter_cblc_to_added_glyphs(base_font, emoji_glyphs_to_add)

    # Step 6: add empty glyph placeholders in glyf table
    # Sarasa is TrueType (has glyf); actual emoji rendering comes from CBDT, not glyf
    if "glyf" in base_font:
        for glyph_name in emoji_glyphs_to_add:
            if glyph_name not in base_glyf.glyphs:
                empty = TTGlyph()
                empty.numberOfContours = 0
                base_glyf[glyph_name] = empty

    # Step 7: set emoji advance width in hmtx (and vmtx if present)
    base_hmtx = base_font["hmtx"]
    for glyph_name in emoji_glyphs_to_add:
        if glyph_name not in base_hmtx.metrics:
            base_hmtx.metrics[glyph_name] = (emoji_width, 0)

    if "vmtx" in base_font:
        base_vmtx = base_font["vmtx"]
        for glyph_name in emoji_glyphs_to_add:
            if glyph_name not in base_vmtx.metrics:
                base_vmtx.metrics[glyph_name] = (emoji_width, 0)

    # Update maxp AFTER glyf is fully populated (avoids loca inconsistency warning)
    base_font["maxp"].numGlyphs = len(new_order)

    # Step 8: update cmap (robust: ensures format=12 table exists for > U+FFFF)
    added_set = set(emoji_glyphs_to_add)
    updated = _update_cmap(base_font, emoji_cmap, added_set)
    print(f"  cmap entries added: {updated}")

    # Step 9: update hhea and OS/2
    if "hhea" in base_font:
        base_font["hhea"].advanceWidthMax = max(
            base_font["hhea"].advanceWidthMax, emoji_width
        )
        base_font["hhea"].numberOfHMetrics = len(base_hmtx.metrics)

    from .utils import merge_os2_ranges
    merge_os2_ranges(base_font, emoji_font)

    # Strip Mac platform name records BEFORE returning
    # Sarasa's original records contain CJK chars that can't be encoded as mac_roman
    # This must happen before update_font_names to avoid re-introducing the issue
    _strip_mac_name_records(base_font)

    emoji_font.close()

    print(f"  Total glyphs after merge: {len(base_font.getGlyphOrder())}")
    if has_cbdt:
        print(f"  CBLC strikes: {len(base_font['CBLC'].strikes)}")

    return base_font
