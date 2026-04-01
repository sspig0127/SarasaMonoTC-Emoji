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
from dataclasses import dataclass
from typing import Optional

from fontTools.ttLib import TTFont
from fontTools.ttLib.tables import _c_m_a_p as cmap_module
from fontTools.ttLib.tables import otTables
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.ttLib.tables._g_l_y_f import Glyph as TTGlyph, GlyphCoordinates, GlyphComponent
from fontTools.otlLib.builder import buildLigatureSubstSubtable, buildLookup

from .config import FontConfig

# TrueType glyph header fields (xMin/yMin/xMax/yMax) and component offsets
# are packed as int16 in the binary format.
_INT16_MIN = -32768
_INT16_MAX = 32767

# Codepoint ranges to skip when extracting emoji
# These are either already handled by Sarasa or are not user-visible emoji
_SKIP_CODEPOINT_RANGES = [
    (0x0000, 0x00FF),    # ASCII + Latin-1 Supplement
    (0xFE00, 0xFE0F),    # Variation Selectors
    (0xE0100, 0xE01EF),  # Variation Selectors Supplement
]


@dataclass(frozen=True)
class EmojiEntry:
    """Normalized emoji metadata shared across variants."""

    codepoints: tuple[int, ...]
    source_glyph: str
    kind: str  # "single" | "sequence"
    source_table_kind: str  # "CBDT" | "glyf" | "COLRv1"


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


def extract_emoji_sequences(emoji_font: TTFont) -> dict[tuple[int, ...], str]:
    """Extract multi-codepoint emoji sequences from GSUB ligatures.

    v1.x only reads the font cmap, which naturally limits the project to
    single-codepoint emoji. Sequence emoji such as ZWJ, skin-tone, and flag
    forms are typically encoded as GSUB ligature substitutions instead.

    This helper scans LookupType 4 (Ligature Substitution) and resolves each
    glyph sequence back to its source Unicode codepoints using the font cmap.
    Unlike get_emoji_cmap(), the reverse cmap here intentionally keeps control
    codepoints such as ZWJ and variation selectors because they are valid
    components of emoji sequences.

    Args:
        emoji_font: TTFont object for an emoji source font

    Returns:
        Dict mapping codepoint tuples -> ligature glyph name
    """
    if "GSUB" not in emoji_font:
        return {}

    raw_cmap = emoji_font["cmap"].getBestCmap() or {}
    glyph_to_codepoint: dict[str, int] = {}
    for cp, glyph_name in raw_cmap.items():
        glyph_to_codepoint.setdefault(glyph_name, cp)

    sequences: dict[tuple[int, ...], str] = {}
    for lookup in emoji_font["GSUB"].table.LookupList.Lookup:
        if lookup.LookupType != 4:
            continue

        for subtable in lookup.SubTable:
            ligatures = getattr(subtable, "ligatures", None) or {}
            for first_glyph, ligature_records in ligatures.items():
                first_cp = glyph_to_codepoint.get(first_glyph)
                if first_cp is None:
                    continue

                for ligature in ligature_records:
                    codepoints = [first_cp]
                    for component_glyph in ligature.Component:
                        cp = glyph_to_codepoint.get(component_glyph)
                        if cp is None:
                            break
                        codepoints.append(cp)
                    else:
                        if len(codepoints) >= 2:
                            sequences[tuple(codepoints)] = ligature.LigGlyph

    return sequences


def collect_emoji_entries(
    emoji_font: TTFont,
    source_table_kind: str,
) -> list[EmojiEntry]:
    """Collect single-codepoint and GSUB-backed sequence emoji metadata."""
    entries = [
        EmojiEntry(
            codepoints=(cp,),
            source_glyph=glyph_name,
            kind="single",
            source_table_kind=source_table_kind,
        )
        for cp, glyph_name in get_emoji_cmap(emoji_font).items()
    ]

    entries.extend(
        EmojiEntry(
            codepoints=codepoints,
            source_glyph=glyph_name,
            kind="sequence",
            source_table_kind=source_table_kind,
        )
        for codepoints, glyph_name in extract_emoji_sequences(emoji_font).items()
    )
    return entries


def _build_sequence_ligature_map(
    sequence_entries: list[EmojiEntry],
    merged_cmap: dict[int, str],
    added_glyphs: set[str],
) -> dict[tuple[str, ...], str]:
    """Resolve sequence entries into GSUB ligature input/output glyph names."""
    ligatures: dict[tuple[str, ...], str] = {}
    for entry in sequence_entries:
        if entry.kind != "sequence" or entry.source_glyph not in added_glyphs:
            continue

        component_names = []
        for cp in entry.codepoints:
            glyph_name = merged_cmap.get(cp)
            if glyph_name is None:
                break
            component_names.append(glyph_name)
        else:
            if len(component_names) >= 2:
                ligatures[tuple(component_names)] = entry.source_glyph

    return ligatures


def _append_ligature_lookup_to_gsub(
    font: TTFont,
    ligature_map: dict[tuple[str, ...], str],
    feature_tag: str = "ccmp",
) -> int:
    """Append a ligature lookup to all matching GSUB features.

    Returns the number of ligature rules appended. If the font lacks a GSUB
    table or there is no usable ligature mapping, this is a no-op.
    """
    if not ligature_map or "GSUB" not in font:
        return 0

    gsub = font["GSUB"].table
    if gsub.LookupList is None or gsub.FeatureList is None:
        return 0

    subtable = buildLigatureSubstSubtable(ligature_map)
    if subtable is None:
        return 0

    lookup = buildLookup([subtable], table="GSUB")
    lookup_index = gsub.LookupList.LookupCount
    gsub.LookupList.Lookup.append(lookup)
    gsub.LookupList.LookupCount += 1

    attached = False
    for feature_record in gsub.FeatureList.FeatureRecord:
        if feature_record.FeatureTag != feature_tag:
            continue
        lookup_indexes = list(feature_record.Feature.LookupListIndex)
        if lookup_index not in lookup_indexes:
            lookup_indexes.append(lookup_index)
            feature_record.Feature.LookupListIndex = lookup_indexes
            feature_record.Feature.LookupCount = len(lookup_indexes)
        attached = True

    if not attached:
        gsub.LookupList.Lookup.pop()
        gsub.LookupList.LookupCount -= 1
        return 0

    return len(ligature_map)


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

    # Fallback: scan hmtx for the most common 2:1 width pair.
    # Require each width to appear in ≥ 1% of all glyphs so that rare/orphan
    # glyphs with an accidental 2:1 ratio don't produce a misleading result.
    widths = Counter(w for w, _ in hmtx.metrics.values() if w > 0)
    total = sum(widths.values())
    min_count = max(1, total // 100)  # 1% threshold
    for w, count in widths.most_common(20):
        if count < min_count:
            continue
        double_count = widths.get(w * 2, 0)
        if double_count >= min_count:
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
    force_codepoints: set[int] | None = None,
) -> int:
    """Add emoji codepoints to font's cmap tables.

    Creates a Windows Unicode format=12 table if not present (required for
    supplementary codepoints > U+FFFF). Also updates format=4 for BMP emoji.

    Args:
        force_codepoints: Codepoints whose cmap entries are overwritten even
            when the entry already exists (used by force_colrv1_codepoints to
            redirect BMP symbols from Sarasa's monochrome glyph to the COLRv1
            stub).

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

        is_forced = force_codepoints is not None and cp in force_codepoints

        # format=12 handles all Unicode planes (BMP + supplementary).
        # For forced codepoints, overwrite even if the entry already exists —
        # this redirects BMP symbols (e.g. U+2764 ❤) from Sarasa's monochrome
        # glyph to our new COLRv1 stub (e.g. uni2764_colrv1).
        if cp not in fmt12_win.cmap or is_forced:
            if cp not in fmt12_win.cmap:
                added += 1
            fmt12_win.cmap[cp] = name

        # Also add BMP emoji to format=4 table for legacy compatibility
        if fmt4_win and cp <= 0xFFFF and (cp not in fmt4_win.cmap or is_forced):
            fmt4_win.cmap[cp] = name

        # Mirror to Unicode platform format=12 if present
        if fmt12_uni and (cp not in fmt12_uni.cmap or is_forced):
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
    removed_names: set[str] = set()

    for strike in cblc.strikes:
        for sub in strike.indexSubTables:
            original_len = len(sub.names)
            valid_idx = [i for i, n in enumerate(sub.names) if n in valid_names]

            if len(valid_idx) == original_len:
                continue

            removed_names.update(
                sub.names[i] for i in range(original_len) if i not in set(valid_idx)
            )
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
        # Sort and show up to 10 sample names so the log is scannable.
        # These are NotoColorEmoji glyph names that conflict with existing Sarasa
        # glyph names; they retain Sarasa's monochrome outline instead of getting
        # the color bitmap.  Use force_color_codepoints to override specific ones.
        samples = sorted(removed_names)[:10]
        suffix = f" … (+{len(removed_names) - 10} more)" if len(removed_names) > 10 else ""
        print(
            f"  Filtered {removed_total} conflicting entries from CBLC IndexSubTables "
            f"({len(removed_names)} unique names: {', '.join(samples)}{suffix})"
        )


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


def _check_int16(value: int, field: str, scale: float) -> None:
    """Raise ValueError if value is outside the int16 range [-32768, 32767].

    Args:
        value: Rounded integer to validate
        field: Field name for the error message (e.g. 'xMax', 'comp.y')
        scale: The scale factor that produced this value (for diagnostics)
    """
    if not (_INT16_MIN <= value <= _INT16_MAX):
        raise ValueError(
            f"_scale_glyph: {field}={value} exceeds int16 range "
            f"[{_INT16_MIN}, {_INT16_MAX}] after scaling by {scale:.6f}. "
            f"Source glyph coordinate is out of range for the target UPM."
        )


def _scale_glyph(glyph, scale: float) -> None:
    """Scale a TrueType glyph's coordinates in-place.

    Required when the source emoji font's UPM differs from the target font's UPM
    (e.g. Noto Emoji uses UPM 2048, Sarasa uses UPM 1000).  Without scaling,
    emoji glyphs appear ~2× too large because their coordinates are in the larger
    unit space but rendered against the target font's smaller metrics.

    Glyph must already be expanded (decompiled) before calling this function.

    Args:
        glyph: Expanded TTGlyph object to scale in-place
        scale: Scale factor (target_upm / source_upm)

    Raises:
        ValueError: If any scaled bbox or component offset exceeds int16 range.
    """
    if abs(scale - 1.0) < 1e-6:
        return  # no-op if same UPM

    from fontTools.misc.roundTools import otRound

    if glyph.numberOfContours > 0:
        # Simple glyph: scale all coordinate points
        glyph.coordinates.scale((scale, scale))
        # calcBounds() may return numpy floats; TrueType glyph header fields
        # (xMin/yMin/xMax/yMax) are packed as int16 — must be rounded integers.
        bounds = glyph.coordinates.calcBounds()
        if bounds is not None:
            xMin = otRound(bounds[0])
            yMin = otRound(bounds[1])
            xMax = otRound(bounds[2])
            yMax = otRound(bounds[3])
            _check_int16(xMin, "xMin", scale)
            _check_int16(yMin, "yMin", scale)
            _check_int16(xMax, "xMax", scale)
            _check_int16(yMax, "yMax", scale)
            glyph.xMin = xMin
            glyph.yMin = yMin
            glyph.xMax = xMax
            glyph.yMax = yMax
    elif glyph.numberOfContours < 0 and hasattr(glyph, "components"):
        # Composite glyph: scale component translation offsets
        for comp in glyph.components:
            x = otRound(comp.x * scale)
            y = otRound(comp.y * scale)
            _check_int16(x, "comp.x", scale)
            _check_int16(y, "comp.y", scale)
            comp.x = x
            comp.y = y


# PoC flag body geometry — tuned for the Sarasa 1000-UPM 2-column emoji slot.
# The outer rectangle spans the full emoji advance; a 35-unit border creates
# the inner space where the two letter glyphs are centered.
_POC_FLAG_X0, _POC_FLAG_X1 = 20, 980
_POC_FLAG_Y0, _POC_FLAG_Y1 = -150, 750
_POC_FLAG_BORDER = 35
_POC_INNER_X0 = _POC_FLAG_X0 + _POC_FLAG_BORDER   # 55
_POC_INNER_X1 = _POC_FLAG_X1 - _POC_FLAG_BORDER   # 945
_POC_INNER_Y0 = _POC_FLAG_Y0 + _POC_FLAG_BORDER   # -115
_POC_INNER_Y1 = _POC_FLAG_Y1 - _POC_FLAG_BORDER   # 715
_POC_INNER_MID_X = (_POC_INNER_X0 + _POC_INNER_X1) // 2   # 500
_POC_LETTER_GAP = 10   # horizontal gap between the two letters at centre
_POC_LEFT_CX = (_POC_INNER_X0 + _POC_INNER_MID_X - _POC_LETTER_GAP) // 2   # 275
_POC_RIGHT_CX = (_POC_INNER_MID_X + _POC_LETTER_GAP + _POC_INNER_X1) // 2  # 725
_POC_CENTER_Y = (_POC_INNER_Y0 + _POC_INNER_Y1) // 2   # 300

# Each letter is condensed (non-uniform x/y scaling) to fill this canonical box.
_POC_LETTER_W = 360
_POC_LETTER_H = 580
# Component offsets to centre the canonical letter box within each letter zone.
_POC_LEFT_LETTER_X = _POC_LEFT_CX - _POC_LETTER_W // 2    # 95
_POC_LEFT_LETTER_Y = _POC_CENTER_Y - _POC_LETTER_H // 2   # 10
_POC_RIGHT_LETTER_X = _POC_RIGHT_CX - _POC_LETTER_W // 2  # 545
_POC_RIGHT_LETTER_Y = _POC_LEFT_LETTER_Y                   # 10


def _scale_simple_glyph_about_center(
    glyph,
    scale_x: float,
    scale_y: float,
) -> None:
    """Scale a simple glyph around its own bbox center."""
    if glyph is None or glyph.numberOfContours <= 0 or not hasattr(glyph, "coordinates"):
        return
    if abs(scale_x - 1.0) < 1e-6 and abs(scale_y - 1.0) < 1e-6:
        return
    if not glyph.coordinates:
        return

    from fontTools.misc.roundTools import otRound

    glyph.recalcBounds(None)
    cx = (glyph.xMin + glyph.xMax) / 2.0
    cy = (glyph.yMin + glyph.yMax) / 2.0

    new_coords = []
    for x, y in glyph.coordinates:
        sx = otRound(cx + ((x - cx) * scale_x))
        sy = otRound(cy + ((y - cy) * scale_y))
        _check_int16(sx, "coord.x", scale_x)
        _check_int16(sy, "coord.y", scale_y)
        new_coords.append((sx, sy))

    glyph.coordinates[:] = new_coords
    glyph.recalcBounds(None)


def _build_poc_flag_template(emoji_width: int) -> TTGlyph:
    """Build a rectangular frame glyph for the PoC 2-column flag body.

    Outer contour is CCW (filled in TrueType y-up coordinates); inner contour
    is CW (creates a hole), producing a visible border frame.
    """
    import array as _array

    x0, x1 = 20, emoji_width - 20
    y0, y1 = _POC_FLAG_Y0, _POC_FLAG_Y1
    b = _POC_FLAG_BORDER
    xi0, xi1 = x0 + b, x1 - b
    yi0, yi1 = y0 + b, y1 - b

    outer = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]     # CCW — filled
    inner = [(xi0, yi0), (xi0, yi1), (xi1, yi1), (xi1, yi0)]  # CW — hole

    g = TTGlyph()
    g.numberOfContours = 2
    g.coordinates = GlyphCoordinates(outer + inner)
    g.flags = _array.array("B", [1] * 8)
    g.endPtsOfContours = [3, 7]
    g.program = Program()
    g.xMin, g.yMin, g.xMax, g.yMax = x0, y0, x1, y1
    return g


def _build_poc_letter_canonical(src_glyph: TTGlyph) -> TTGlyph:
    """Build a condensed copy of a letter glyph scaled to the canonical PoC box.

    X and Y are scaled independently so the letter fills _POC_LETTER_W ×
    _POC_LETTER_H exactly (condensed proportions). The result sits at [0..W, 0..H].
    Composite glyphs are not transformed — caller should expand() before calling.
    """
    from fontTools.misc.roundTools import otRound

    if (
        src_glyph is None
        or src_glyph.numberOfContours <= 0
        or not hasattr(src_glyph, "coordinates")
        or not src_glyph.coordinates
    ):
        empty = TTGlyph()
        empty.numberOfContours = 0
        empty.program = Program()
        return empty

    src_glyph.recalcBounds(None)
    src_w = src_glyph.xMax - src_glyph.xMin
    src_h = src_glyph.yMax - src_glyph.yMin
    if src_w <= 0 or src_h <= 0:
        return copy.deepcopy(src_glyph)

    scale_x = _POC_LETTER_W / src_w
    scale_y = _POC_LETTER_H / src_h
    tx = -src_glyph.xMin
    ty = -src_glyph.yMin

    g = copy.deepcopy(src_glyph)
    new_coords = []
    for x, y in g.coordinates:
        nx = otRound((x + tx) * scale_x)
        ny = otRound((y + ty) * scale_y)
        _check_int16(nx, "poc_letter.x", scale_x)
        _check_int16(ny, "poc_letter.y", scale_y)
        new_coords.append((nx, ny))
    g.coordinates = GlyphCoordinates(new_coords)
    g.program = Program()
    g.recalcBounds(None)
    return g


def _is_regional_indicator_flag_sequence(codepoints: tuple[int, ...]) -> bool:
    """Return True for standard two-codepoint regional-indicator flags."""
    return (
        len(codepoints) == 2
        and all(0x1F1E6 <= cp <= 0x1F1FF for cp in codepoints)
    )


def _build_lite_flag_poc(
    base_font: TTFont,
    sequence_entries: list[EmojiEntry],
    base_hmtx,
    base_vmtx,
    emoji_width: int,
) -> int:
    """Build custom 2-column flag composites for all RI-pair flag sequences.

    Replaces the old scaling-only approach. For each supported flag:
      1. Creates a shared flag body template glyph sized for the 1000-wide slot.
      2. Builds condensed letter copies (independently scaled to _POC_LETTER_W ×
         _POC_LETTER_H) for every unique letter component found in the composites.
      3. Rebuilds the flag ligature glyphs as 3-component composites:
          flag-template + left-letter + right-letter, with offsets that centre
          each letter in its half of the flag interior.

    Only standard regional-indicator flag sequences are rebuilt; ZWJ and skin-tone
    sequences remain untouched. Letters shared across flags (e.g. C in 🇨🇳/🇨🇦) reuse the same canonical
    glyph. Returns the total number of new helper glyphs added.
    """
    base_glyf = base_font["glyf"]
    current_order = list(base_font.getGlyphOrder())
    added_names: list[str] = []

    entries_by_codepoints = {
        entry.codepoints: entry
        for entry in sequence_entries
        if _is_regional_indicator_flag_sequence(entry.codepoints)
    }
    if not entries_by_codepoints:
        return 0

    # --- Step 1: shared flag body template ---
    template_name = "poc_lite_flag_template"
    if template_name not in base_glyf.glyphs:
        base_glyf[template_name] = _build_poc_flag_template(emoji_width)
        current_order.append(template_name)
        added_names.append(template_name)
        base_hmtx.metrics[template_name] = (emoji_width, 0)
        if base_vmtx is not None:
            base_vmtx.metrics[template_name] = (emoji_width, 0)

    # --- Step 2: condensed letter copies ---
    # Maps original letter glyph name → canonical PoC glyph name.
    letter_map: dict[str, str] = {}

    for entry in entries_by_codepoints.values():
        if entry.source_glyph not in base_glyf.glyphs:
            continue

        ligature = base_glyf[entry.source_glyph]
        ligature.expand(base_glyf)
        components = getattr(ligature, "components", None) or []
        if ligature.numberOfContours >= 0 or len(components) < 3:
            continue

        for comp in components[1:3]:
            orig_name = comp.glyphName
            if orig_name in letter_map or orig_name not in base_glyf.glyphs:
                continue

            poc_name = f"poc_lite_letter.{orig_name}"
            if poc_name not in base_glyf.glyphs:
                src = base_glyf[orig_name]
                if hasattr(src, "expand"):
                    src.expand(base_glyf)
                canonical = _build_poc_letter_canonical(src)
                base_glyf[poc_name] = canonical
                current_order.append(poc_name)
                added_names.append(poc_name)
                base_hmtx.metrics[poc_name] = (emoji_width, 0)
                if base_vmtx is not None:
                    base_vmtx.metrics[poc_name] = (emoji_width, 0)

            letter_map[orig_name] = poc_name

    # --- Step 3: rebuild flag composites ---
    def _comp(name: str, x: int, y: int) -> GlyphComponent:
        c = GlyphComponent()
        c.glyphName = name
        c.flags = 0
        c.x = x
        c.y = y
        return c

    for entry in entries_by_codepoints.values():
        if entry.source_glyph not in base_glyf.glyphs:
            continue

        ligature = base_glyf[entry.source_glyph]
        ligature.expand(base_glyf)
        components = getattr(ligature, "components", None) or []
        if ligature.numberOfContours >= 0 or len(components) < 3:
            continue

        left_poc = letter_map.get(components[1].glyphName)
        right_poc = letter_map.get(components[2].glyphName)
        if left_poc is None or right_poc is None:
            continue

        new_g = TTGlyph()
        new_g.numberOfContours = -1
        new_g.components = [
            _comp(template_name, 0, 0),
            _comp(left_poc, _POC_LEFT_LETTER_X, _POC_LEFT_LETTER_Y),
            _comp(right_poc, _POC_RIGHT_LETTER_X, _POC_RIGHT_LETTER_Y),
        ]
        new_g.program = Program()
        new_g.recalcBounds(base_glyf)
        base_glyf[entry.source_glyph] = new_g

    if added_names:
        base_font.setGlyphOrder(current_order)

    return len(added_names)


def _collect_glyph_deps(
    emoji_font: TTFont,
    target_names: set[str],
    base_existing_names: set[str],
) -> list[str]:
    """Collect emoji glyphs including composite dependencies.

    For composite glyphs, component glyphs are visited first so their glyph
    IDs are always lower than (and thus valid references for) the composites.

    Args:
        emoji_font: Source emoji font (glyf-based, e.g. Noto Emoji monochrome)
        target_names: Glyph names needed from cmap (name conflicts already removed)
        base_existing_names: Names already in base font (skip these)

    Returns:
        Ordered list of glyph names to add (components before composites)
    """
    emoji_glyf = emoji_font.get("glyf")
    if emoji_glyf is None:
        return [n for n in target_names if n not in base_existing_names]

    result: list[str] = []
    seen = set(base_existing_names)

    def visit(name: str) -> None:
        if name in seen:
            return
        seen.add(name)
        if name not in emoji_glyf.glyphs:
            return
        glyph = emoji_glyf[name]
        glyph.expand(emoji_glyf)  # decompile (no-op if already expanded)
        if glyph.numberOfContours < 0 and hasattr(glyph, "components"):
            for comp in glyph.components:
                visit(comp.glyphName)
        result.append(name)

    for name in target_names:
        visit(name)

    return result


def merge_emoji_lite(
    base_font_path: str,
    emoji_font_path: str,
    config: FontConfig,
    force_codepoints: set[int] | None = None,
) -> TTFont:
    """Merge Noto Emoji glyf outlines (monochrome) into SarasaMonoTC.

    Unlike merge_emoji() which uses CBDT/CBLC color bitmap tables, this
    function copies glyf TrueType outlines directly — no bitmap tables needed.

    Advantages over color variant:
    - Smaller output file (~60% smaller; no bitmap data)
    - Full Chromium/xterm.js compatibility (required for VHS recording)
    - Emoji render in the terminal's foreground text color
    - Works on every renderer that supports TrueType outlines

    Args:
        base_font_path: Path to SarasaMonoTC-{Style}.ttf
        emoji_font_path: Path to NotoEmoji-Regular.ttf (glyf-based font)
        config: FontConfig object
        force_codepoints: BMP codepoints to force Lite outline override even
            when skip_existing=True. Conflicting glyph names are renamed with
            a `_lite` suffix so the Noto outline can coexist with Sarasa.

    Returns:
        Merged TTFont object (caller must call .save() and .close())
    """
    print(f"  Loading base font: {base_font_path}")
    base_font = TTFont(base_font_path, lazy=True, recalcBBoxes=False)
    print(f"  Loading emoji font: {emoji_font_path}")
    emoji_font = TTFont(emoji_font_path)

    # Step 1: detect widths
    half_width, full_width = detect_font_widths(base_font)
    emoji_width = half_width * config.emoji_width_multiplier
    print(f"  Detected widths — half: {half_width}, full: {full_width}, emoji: {emoji_width}")

    # Step 2: collect shared emoji metadata (single codepoints + sequences)
    emoji_entries = collect_emoji_entries(emoji_font, source_table_kind="glyf")
    emoji_cmap = {
        entry.codepoints[0]: entry.source_glyph
        for entry in emoji_entries
        if entry.kind == "single"
    }
    sequence_entries = [entry for entry in emoji_entries if entry.kind == "sequence"]
    print(
        f"  Emoji entries: {len(emoji_entries)} "
        f"(single: {len(emoji_cmap)}, sequence: {len(sequence_entries)})"
    )

    base_existing_names = set(base_font.getGlyphOrder())

    # Step 2.5: build rename map for forced BMP codepoints that conflict with Sarasa.
    lite_forced_rename: dict[str, str] = {}
    if force_codepoints:
        for cp in force_codepoints:
            if cp in emoji_cmap:
                orig_name = emoji_cmap[cp]
                if orig_name in base_existing_names:
                    lite_forced_rename[orig_name] = f"{orig_name}_lite"
        if lite_forced_rename:
            print(
                f"  Forced Lite BMP renames: {len(lite_forced_rename)} "
                f"(e.g. {next(iter(lite_forced_rename))} → "
                f"{next(iter(lite_forced_rename.values()))})"
            )
        emoji_cmap = {
            cp: lite_forced_rename.get(name, name)
            for cp, name in emoji_cmap.items()
        }

    # Step 3: filter existing codepoints
    if config.skip_existing:
        base_cmap = base_font["cmap"].getBestCmap() or {}
        before = len(emoji_cmap)
        emoji_cmap = {
            cp: name
            for cp, name in emoji_cmap.items()
            if cp not in base_cmap or (force_codepoints is not None and cp in force_codepoints)
        }
        print(f"  Filtered existing codepoints: {before} → {len(emoji_cmap)}")

    if not emoji_cmap:
        print("  No new emoji to add.")
        emoji_font.close()
        return base_font

    if "glyf" not in emoji_font:
        raise ValueError(
            f"Emoji font '{emoji_font_path}' has no glyf table. "
            "Lite variant requires a glyf-based font (e.g. NotoEmoji-Regular.ttf). "
            "Use NotoColorEmoji.ttf with build.py (without --lite) for the color variant."
        )

    # Collect glyph names that need to be added from both single-codepoint and
    # sequence outputs. Sequence input components are resolved later via cmap
    # and existing base glyphs; only the final ligature glyph needs copying here.
    target_source_names = {
        entry.source_glyph
        for entry in emoji_entries
        if entry.source_glyph not in base_existing_names or entry.source_glyph in lite_forced_rename
    }

    # Expand with composite dependencies (components must precede composites)
    dep_skip_names = base_existing_names - set(lite_forced_rename)
    source_glyphs_to_add = _collect_glyph_deps(emoji_font, target_source_names, dep_skip_names)
    emoji_glyphs_to_add = [lite_forced_rename.get(name, name) for name in source_glyphs_to_add]
    lite_rename_to_orig = {v: k for k, v in lite_forced_rename.items()}

    unique_source_glyphs = {entry.source_glyph for entry in emoji_entries}
    name_conflicts = len(unique_source_glyphs) - len(target_source_names)
    print(
        f"  Emoji glyphs to add: {len(emoji_glyphs_to_add)} "
        f"(name conflicts: {name_conflicts})"
    )

    # Calculate UPM scale: Noto Emoji uses UPM 2048, Sarasa uses UPM 1000.
    # Without scaling, emoji coordinates are ~2× too large in the target font's
    # unit space and will render significantly taller than surrounding text.
    base_upm = base_font["head"].unitsPerEm
    emoji_upm = emoji_font["head"].unitsPerEm
    upm_scale = base_upm / emoji_upm
    if abs(upm_scale - 1.0) > 1e-6:
        print(f"  UPM scale: {emoji_upm} → {base_upm} (×{upm_scale:.4f})")

    # Access glyf BEFORE setGlyphOrder to avoid OTS flag-encoding issue
    # (same reasoning as merge_emoji — see inline comment there)
    base_glyf = base_font["glyf"]
    emoji_glyf = emoji_font["glyf"]

    # Step 4: append emoji glyphs to glyph order
    original_order = base_font.getGlyphOrder()
    new_order = original_order + emoji_glyphs_to_add
    base_font.setGlyphOrder(new_order)

    # Step 5: copy glyf outlines from Noto Emoji into base font, scaled to target UPM.
    # _collect_glyph_deps() already called glyph.expand(), so src is fully decompiled.
    copied = 0
    for glyph_name in emoji_glyphs_to_add:
        if glyph_name not in base_glyf.glyphs:
            src_name = lite_rename_to_orig.get(glyph_name, glyph_name)
            src = emoji_glyf.glyphs.get(src_name)
            if src is not None:
                glyph_copy = copy.deepcopy(src)
                _scale_glyph(glyph_copy, upm_scale)
                base_glyf[glyph_name] = glyph_copy
                copied += 1
            else:
                empty = TTGlyph()
                empty.numberOfContours = 0
                base_glyf[glyph_name] = empty
    print(f"  Copied {copied} glyph outlines from emoji font (scaled ×{upm_scale:.4f})")

    # Scaling summary: collect bbox range across all copied glyphs so the caller
    # can verify the scale result relative to Sarasa's ascender/descender at a glance.
    if abs(upm_scale - 1.0) > 1e-6 and copied > 0:
        ymin_vals: list[int] = []
        ymax_vals: list[int] = []
        for name in emoji_glyphs_to_add:
            g = base_glyf.glyphs.get(name)
            if g is not None and hasattr(g, "yMax") and g.numberOfContours != 0:
                ymin_vals.append(getattr(g, "yMin", 0))
                ymax_vals.append(getattr(g, "yMax", 0))
        if ymin_vals:
            print(
                f"  Scaled bbox summary: "
                f"yMin [{min(ymin_vals)}..{max(ymin_vals)}], "
                f"yMax [{min(ymax_vals)}..{max(ymax_vals)}] "
                f"({len(ymin_vals)} glyphs sampled)"
            )

    # Step 6: update hmtx (and vmtx if present)
    # IMPORTANT: access vmtx BEFORE updating maxp.numGlyphs.
    # vmtx.decompile() reads maxp.numGlyphs to compute expected byte count.
    # If maxp is updated first, fonttools expects more bytes than the raw data
    # provides (old count) and raises TTLibError.  Same ordering as merge_emoji().
    base_hmtx = base_font["hmtx"]
    for glyph_name in emoji_glyphs_to_add:
        if glyph_name not in base_hmtx.metrics:
            base_hmtx.metrics[glyph_name] = (emoji_width, 0)

    if "vmtx" in base_font:
        base_vmtx = base_font["vmtx"]
        for glyph_name in emoji_glyphs_to_add:
            if glyph_name not in base_vmtx.metrics:
                base_vmtx.metrics[glyph_name] = (emoji_width, 0)
    else:
        base_vmtx = None

    tuned_flag_components = _build_lite_flag_poc(
        base_font,
        sequence_entries,
        base_hmtx,
        base_vmtx,
        emoji_width,
    )
    if tuned_flag_components:
        print(f"  Built Lite PoC flag glyphs: {tuned_flag_components} helper glyphs added")

    # Update maxp AFTER all table accesses (avoids vmtx decompile byte-count mismatch)
    base_font["maxp"].numGlyphs = len(base_font.getGlyphOrder())

    # Step 7: update cmap
    added_set = set(emoji_glyphs_to_add)
    updated = _update_cmap(base_font, emoji_cmap, added_set, force_codepoints)
    print(f"  cmap entries added: {updated}")

    # Step 7.5: append sequence ligatures to the existing GSUB.
    merged_cmap = base_font["cmap"].getBestCmap() or {}
    ligature_map = _build_sequence_ligature_map(sequence_entries, merged_cmap, added_set)
    appended_sequences = _append_ligature_lookup_to_gsub(base_font, ligature_map)
    if appended_sequences:
        print(f"  GSUB sequence ligatures appended: {appended_sequences}")

    # Step 8: update hhea and OS/2
    if "hhea" in base_font:
        base_font["hhea"].advanceWidthMax = max(
            base_font["hhea"].advanceWidthMax, emoji_width
        )
        base_font["hhea"].numberOfHMetrics = len(base_hmtx.metrics)

    from .utils import merge_os2_ranges
    merge_os2_ranges(base_font, emoji_font)

    # Persist _lite glyph names across save/reload when forced BMP overrides are active.
    if lite_forced_rename and "post" in base_font:
        post = base_font["post"]
        _ = post.formatType
        if post.formatType == 3.0:
            print("  Upgrading post table 3.0→2.0 to persist forced Lite glyph names")
            post.formatType = 2.0
            if not hasattr(post, "extraNames"):
                post.extraNames = []
            if not hasattr(post, "mapping"):
                post.mapping = {}

    _strip_mac_name_records(base_font)

    emoji_font.close()
    print(f"  Total glyphs after merge: {len(base_font.getGlyphOrder())}")
    return base_font


def merge_emoji(
    base_font_path: str,
    emoji_font_path: str,
    config: FontConfig,
    force_codepoints: set[int] | None = None,
) -> TTFont:
    """Merge NotoColorEmoji CBDT/CBLC color emoji into SarasaMonoTC.

    Steps:
    1. Load fonts, detect Sarasa's half/full width at runtime
    2. Extract emoji cmap (single codepoints only)
    3. Filter out codepoints already in Sarasa (keep forced ones)
    3.5. Build color_forced_rename for BMP name conflicts; apply to emoji_cmap
    4. Deep-copy CBDT/CBLC tables into Sarasa
       (fonttools recompiles with correct glyph IDs on save)
    4.5. Rename forced glyphs in CBLC IndexSubTables
    5. Append emoji glyph names to glyph order (contiguous block at end)
    6. Add empty glyph placeholders in glyf table
    7. Set emoji advance width in hmtx (= full_width, i.e. 2x half-width)
    8. Update cmap with emoji codepoints (overwrite BMP for forced ones)
    9. Update maxp, hhea, OS/2

    Args:
        base_font_path: Path to SarasaMonoTC-{Style}.ttf
        emoji_font_path: Path to NotoColorEmoji.ttf
        config: FontConfig object
        force_codepoints: BMP codepoints to force color even when skip_existing=True.
            For each codepoint whose emoji glyph name conflicts with Sarasa, a renamed
            glyph (e.g. uni2764 → uni2764_color) is inserted so both the Sarasa outline
            and the color bitmap can coexist; the cmap is redirected to the color version.

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

    # Step 2: collect shared emoji metadata (single codepoints + sequences)
    emoji_entries = collect_emoji_entries(emoji_font, source_table_kind="CBDT")
    emoji_cmap = {
        entry.codepoints[0]: entry.source_glyph
        for entry in emoji_entries
        if entry.kind == "single"
    }
    sequence_entries = [entry for entry in emoji_entries if entry.kind == "sequence"]
    print(
        f"  Emoji entries: {len(emoji_entries)} "
        f"(single: {len(emoji_cmap)}, sequence: {len(sequence_entries)})"
    )

    # Step 3: filter existing codepoints (keep forced ones)
    if config.skip_existing:
        base_cmap = base_font["cmap"].getBestCmap() or {}
        before = len(emoji_cmap)
        emoji_cmap = {
            cp: name for cp, name in emoji_cmap.items()
            if cp not in base_cmap or (force_codepoints is not None and cp in force_codepoints)
        }
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

    # Step 3.5: build rename map for forced BMP codepoints.
    # For each forced codepoint whose emoji glyph name conflicts with Sarasa,
    # we use a renamed glyph (e.g. uni2764 → uni2764_color) so both the Sarasa
    # monochrome outline and the new color bitmap glyph can coexist.
    color_forced_rename: dict[str, str] = {}
    if force_codepoints:
        for cp in force_codepoints:
            if cp in emoji_cmap:
                orig_name = emoji_cmap[cp]
                if orig_name in base_existing_names:
                    color_forced_rename[orig_name] = f"{orig_name}_color"
        if color_forced_rename:
            print(f"  Forced BMP renames: {len(color_forced_rename)} "
                  f"(e.g. {next(iter(color_forced_rename))} → "
                  f"{next(iter(color_forced_rename.values()))})")
        # Apply renames to emoji_cmap so _update_cmap uses the new names
        emoji_cmap = {
            cp: color_forced_rename.get(name, name)
            for cp, name in emoji_cmap.items()
        }

    # Build emoji_glyphs_to_add preserving NotoColorEmoji's glyph ID order.
    # For forced-renamed glyphs: include them under the new name even though the
    # original name conflicts with Sarasa (CBLC strictly-increasing ID requirement
    # means we must keep the relative order from NotoColorEmoji's glyph list).
    emoji_glyphs_to_add = [
        color_forced_rename.get(name, name)
        for name in emoji_all_glyph_order
        if name not in base_existing_names or name in color_forced_rename
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

    # Step 4.5: rename forced glyphs in CBLC IndexSubTables AND CBDT strikeData.
    # Both tables are keyed by glyph name and must stay in sync:
    # - CBLC IndexSubTable.names: maps glyph name → offset (used by _filter_cblc)
    # - CBDT.strikeData[i]: dict mapping glyph name → bitmap object (keyed by name)
    # If only CBLC is renamed and CBDT is not, compile raises KeyError on the new name.
    if color_forced_rename and has_cbdt:
        if "CBLC" in base_font:
            for strike in base_font["CBLC"].strikes:
                for sub in strike.indexSubTables:
                    sub.names = [color_forced_rename.get(n, n) for n in sub.names]
        if "CBDT" in base_font:
            for strike_dict in base_font["CBDT"].strikeData:
                for old_name, new_name in color_forced_rename.items():
                    if old_name in strike_dict:
                        strike_dict[new_name] = strike_dict.pop(old_name)

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
    # For forced BMP codepoints, overwrite existing cmap entries so the renamed
    # color glyph (e.g. uni2764_color) takes precedence over Sarasa's monochrome one.
    added_set = set(emoji_glyphs_to_add)
    updated = _update_cmap(base_font, emoji_cmap, added_set, force_codepoints)
    print(f"  cmap entries added: {updated}")

    # Step 8.5: append sequence ligatures to the existing GSUB.
    merged_cmap = base_font["cmap"].getBestCmap() or {}
    ligature_map = _build_sequence_ligature_map(sequence_entries, merged_cmap, added_set)
    appended_sequences = _append_ligature_lookup_to_gsub(base_font, ligature_map)
    if appended_sequences:
        print(f"  GSUB sequence ligatures appended: {appended_sequences}")

    # Step 9: update hhea and OS/2
    if "hhea" in base_font:
        base_font["hhea"].advanceWidthMax = max(
            base_font["hhea"].advanceWidthMax, emoji_width
        )
        base_font["hhea"].numberOfHMetrics = len(base_hmtx.metrics)

    from .utils import merge_os2_ranges
    merge_os2_ranges(base_font, emoji_font)

    # Step 9.5: if forced BMP renames are active, upgrade post table to format 2.0.
    # Sarasa uses post format 3.0 (no stored glyph names). On reload, fonttools
    # derives glyph names from the cmap reverse-lookup:
    #   cmap[U+2764] → glyph ID X → _makeGlyphName(0x2764) → "uni2764"
    # This silently discards the "_color" suffix we assigned.
    # Format 2.0 writes an explicit name string for every glyph in the font,
    # so "uni2764_color" survives the save/reload cycle unchanged.
    if color_forced_rename and "post" in base_font:
        post = base_font["post"]
        _ = post.formatType  # trigger lazy decompile
        if post.formatType == 3.0:
            print("  Upgrading post table 3.0→2.0 to persist forced-rename glyph names")
            post.formatType = 2.0
            if not hasattr(post, "extraNames"):
                post.extraNames = []
            if not hasattr(post, "mapping"):
                post.mapping = {}

    # Strip Mac platform name records BEFORE returning
    # Sarasa's original records contain CJK chars that can't be encoded as mac_roman
    # This must happen before update_font_names to avoid re-introducing the issue
    _strip_mac_name_records(base_font)

    emoji_font.close()

    print(f"  Total glyphs after merge: {len(base_font.getGlyphOrder())}")
    if has_cbdt:
        print(f"  CBLC strikes: {len(base_font['CBLC'].strikes)}")

    return base_font


# ---------------------------------------------------------------------------
# COLRv1 variant
# ---------------------------------------------------------------------------

def _select_colrv1_emoji_greedy(
    emoji_cmap: dict[int, str],
    emoji_font: TTFont,
    max_new_glyphs: int,
    priority_codepoints: set[int] | None = None,
) -> tuple[dict[int, str], list[dict]]:
    """Greedy selection of COLRv1 emoji within a glyph slot budget.

    Selection runs in two phases:

    **Phase 1 — Priority emoji**: Codepoints listed in *priority_codepoints*
    are selected first (in codepoint order), regardless of their position in
    the overall sorted sequence.  This guarantees that important dev/tooling
    emoji (e.g. 🔧🔗🚀🔒) are always included even though they have higher
    codepoints than the phase-2 cutoff.  Priority emoji still consume budget.

    **Phase 2 — Greedy fill**: Remaining emoji are iterated in codepoint
    ascending order.  Each emoji (and its new geometry deps) is added while
    cumulative cost stays within *max_new_glyphs*.  Stops at the first
    over-budget emoji (no skip-and-continue).

    Geometry deps are shared across both phases: a dep already paid for by a
    previously selected emoji does not count again toward the budget.

    Args:
        emoji_cmap: Full codepoint→glyph_name mapping (after existing-cp filter).
        emoji_font: Source COLRv1 font (must have COLR table).
        max_new_glyphs: Maximum total new glyphs (emoji stubs + geometry deps).
        priority_codepoints: Codepoints that must be selected before the greedy
            phase.  Ignored if None or empty.

    Returns:
        (filtered_cmap, selection_records) where selection_records is a list
        of dicts, one per selected emoji:
          - codepoint: "U+1F600"
          - char: "😀"
          - glyph_name: "u1F600"
          - unicode_name: "GRINNING FACE"
          - geometry_deps_count: total deps referenced by this emoji's paint tree
          - new_glyph_cost: actual new glyph slots consumed (1 + unseen deps)
          - priority: True if selected via priority list
    """
    import unicodedata

    selected_cmap: dict[int, str] = {}
    selection_records: list[dict] = []
    accumulated_deps: set[str] = set()
    total_cost = 0

    def _select_one(cp: int, is_priority: bool) -> bool:
        """Try to select one emoji; return True if selected."""
        nonlocal total_cost
        if cp not in emoji_cmap or cp in selected_cmap:
            return False
        glyph_name = emoji_cmap[cp]
        deps = _collect_colrv1_paint_glyph_deps(emoji_font, {glyph_name})
        deps.discard(glyph_name)
        new_deps = deps - accumulated_deps
        cost = 1 + len(new_deps)
        if total_cost + cost > max_new_glyphs:
            return False
        selected_cmap[cp] = glyph_name
        accumulated_deps.update(new_deps)
        total_cost += cost
        try:
            char = chr(cp)
            unicode_name = unicodedata.name(char, "UNKNOWN")
        except (ValueError, TypeError):
            char = f"U+{cp:04X}"
            unicode_name = "UNKNOWN"
        selection_records.append({
            "codepoint": f"U+{cp:04X}",
            "char": char,
            "glyph_name": glyph_name,
            "unicode_name": unicode_name,
            "geometry_deps_count": len(deps),
            "new_glyph_cost": cost,
            "priority": is_priority,
        })
        return True

    # Phase 1: priority emoji (sorted for deterministic output)
    priority_set = priority_codepoints or set()
    priority_selected = 0
    for cp in sorted(priority_set):
        if _select_one(cp, is_priority=True):
            priority_selected += 1

    # Phase 2: greedy fill — codepoint ascending, stop at first over-budget
    for cp in sorted(emoji_cmap):
        if cp in selected_cmap:
            continue  # already selected in phase 1
        if not _select_one(cp, is_priority=False):
            break  # greedy: stop at first over-budget emoji

    print(
        f"  Greedy selection: {len(selected_cmap)}/{len(emoji_cmap)} emoji selected "
        f"({priority_selected} priority), total glyph cost: {total_cost}/{max_new_glyphs}"
    )
    return selected_cmap, selection_records


def _collect_colrv1_paint_glyph_deps(
    emoji_font: TTFont,
    target_names: set[str],
) -> set[str]:
    """Collect geometry helper glyph names referenced by PaintGlyph nodes.

    Walks the COLRv1 BaseGlyphPaintRecord for each glyph in target_names,
    recursing through all paint tree nodes to find PaintGlyph (Format=10)
    references.  These are geometry helper glyphs whose TrueType outlines
    are used as clip shapes and must be copied alongside the emoji glyphs.

    Args:
        emoji_font: Source emoji font with COLR v1 table
        target_names: Glyph names we intend to copy (from cmap, no conflicts)

    Returns:
        Set of geometry dep glyph names (may overlap with target_names if
        an emoji glyph reuses another emoji glyph as a clip shape)
    """
    if "COLR" not in emoji_font:
        return set()
    colr = emoji_font["COLR"].table
    if not hasattr(colr, "BaseGlyphList") or colr.BaseGlyphList is None:
        return set()

    layer_list = getattr(colr, "LayerList", None)
    deps: set[str] = set()

    def walk(paint) -> None:
        if paint is None:
            return
        fmt = getattr(paint, "Format", None)
        if fmt == 10:  # PaintGlyph — references a geometry helper
            deps.add(paint.Glyph)
            walk(paint.Paint)
        elif fmt == 1:  # PaintColrLayers — indirect refs via LayerList
            if layer_list is not None:
                first = paint.FirstLayerIndex
                for layer in layer_list.Paint[first : first + paint.NumLayers]:
                    walk(layer)
        else:
            for attr in ("Paint", "SourcePaint", "BackdropPaint"):
                child = getattr(paint, attr, None)
                if child is not None:
                    walk(child)
            for child in getattr(paint, "Paints", []) or []:
                walk(child)

    for record in colr.BaseGlyphList.BaseGlyphPaintRecord:
        if record.BaseGlyph in target_names:
            walk(record.Paint)

    return deps


def _select_colrv1_sequences_greedy(
    sequence_entries: list[EmojiEntry],
    emoji_font: TTFont,
    remaining_budget: int,
    selected_emoji_names: set[str],
    existing_deps: set[str],
    priority_sequences: list[tuple[int, ...]] | None = None,
) -> tuple[list[EmojiEntry], set[str]]:
    """Select COLRv1 sequence glyphs within remaining glyph budget.

    Sequence glyphs are expensive in COLRv1 because each ligature glyph may
    introduce many new geometry helper glyphs. To preserve the existing COLRv1
    glyph-budget behavior, we greedily add sequence entries in codepoint order
    until the remaining budget would be exceeded.
    """
    if remaining_budget <= 0 or not sequence_entries:
        return [], set()

    selected: list[EmojiEntry] = []
    selected_names: set[str] = set()
    accumulated_deps: set[str] = set()
    total_cost = 0
    occupied = set(selected_emoji_names) | set(existing_deps)

    priority_order = priority_sequences or []
    priority_set = set(priority_order)
    entries_by_codepoints = {entry.codepoints: entry for entry in sequence_entries}

    def try_add(entry: EmojiEntry) -> bool:
        nonlocal total_cost
        if entry.source_glyph in occupied or entry.source_glyph in selected_names:
            return False

        deps = _collect_colrv1_paint_glyph_deps(emoji_font, {entry.source_glyph})
        new_deps = deps - occupied - selected_names - accumulated_deps - {entry.source_glyph}
        cost = 1 + len(new_deps)
        if total_cost + cost > remaining_budget:
            return False

        selected.append(entry)
        selected_names.add(entry.source_glyph)
        accumulated_deps.update(new_deps)
        total_cost += cost
        return True

    for codepoints in priority_order:
        entry = entries_by_codepoints.get(codepoints)
        if entry is not None:
            try_add(entry)

    for entry in sorted(sequence_entries, key=lambda e: e.codepoints):
        if entry.codepoints in priority_set:
            continue
        if not try_add(entry):
            break

    return selected, accumulated_deps


def _estimate_colrv1_priority_sequence_cost(
    sequence_entries: list[EmojiEntry],
    emoji_font: TTFont,
    priority_sequences: list[tuple[int, ...]] | None,
) -> int:
    """Estimate the glyph-slot cost of the configured priority sequences."""
    if not priority_sequences:
        return 0

    entries_by_codepoints = {entry.codepoints: entry for entry in sequence_entries}
    selected = [
        entries_by_codepoints[codepoints]
        for codepoints in priority_sequences
        if codepoints in entries_by_codepoints
    ]
    if not selected:
        return 0

    seq_glyphs = {entry.source_glyph for entry in selected}
    deps = _collect_colrv1_paint_glyph_deps(emoji_font, seq_glyphs)
    return len(seq_glyphs | deps)


def _apply_colrv1_rename(paint, rename_map: dict[str, str]) -> None:
    """Recursively rename PaintGlyph.Glyph references in a COLRv1 paint tree."""
    if paint is None:
        return
    fmt = getattr(paint, "Format", None)
    if fmt == 10:  # PaintGlyph
        if paint.Glyph in rename_map:
            paint.Glyph = rename_map[paint.Glyph]
        _apply_colrv1_rename(paint.Paint, rename_map)
    else:
        for attr in ("Paint", "SourcePaint", "BackdropPaint"):
            child = getattr(paint, attr, None)
            if child is not None:
                _apply_colrv1_rename(child, rename_map)
        for child in getattr(paint, "Paints", []) or []:
            _apply_colrv1_rename(child, rename_map)


def _scale_colrv1_paint_coords(colr_obj, upm_scale: float) -> None:
    """Scale font-unit coordinates in a COLRv1 table by upm_scale.

    When merging from a source font with a different UPM (e.g. Noto-COLRv1
    UPM=1024) into a target font with a different UPM (e.g. Sarasa UPM=1000),
    unitless paint values (scale ratios, rotation angles) stay unchanged, but
    font-unit coordinates must be scaled by target_upm / source_upm.

    Fields scaled per format:
    - Format 12/13 (PaintTransform/Var): Transform.dx, Transform.dy
    - Format 14/15 (PaintTranslate/Var): dx, dy
    - Format 4/5  (PaintLinearGradient/Var): x0,y0,x1,y1,x2,y2
    - Format 6/7  (PaintRadialGradient/Var): x0,y0,r0,x1,y1,r1
    - Format 8/9  (PaintSweepGradient/Var): centerX, centerY
    - Any format with centerX / centerY attributes (scale/rotate/skew variants)
    - ClipList bounding boxes: xMin, yMin, xMax, yMax
    """
    if abs(upm_scale - 1.0) < 1e-6:
        return

    from fontTools.misc.roundTools import otRound

    def scale_paint(paint) -> None:
        if paint is None:
            return
        fmt = getattr(paint, "Format", None)

        if fmt in (12, 13):  # PaintTransform / PaintVarTransform
            # Affine2x3 dx/dy are F16Dot16 (float) — keep fractional part
            t = paint.Transform
            t.dx *= upm_scale
            t.dy *= upm_scale
        elif fmt in (14, 15):  # PaintTranslate / PaintVarTranslate
            # dx/dy are FWORD (int16) — must round
            paint.dx = otRound(paint.dx * upm_scale)
            paint.dy = otRound(paint.dy * upm_scale)
        elif fmt in (4, 5):  # PaintLinearGradient / Var — FWORD coords
            for attr in ("x0", "y0", "x1", "y1", "x2", "y2"):
                if hasattr(paint, attr):
                    setattr(paint, attr, otRound(getattr(paint, attr) * upm_scale))
        elif fmt in (6, 7):  # PaintRadialGradient / Var — FWORD coords
            for attr in ("x0", "y0", "r0", "x1", "y1", "r1"):
                if hasattr(paint, attr):
                    setattr(paint, attr, otRound(getattr(paint, attr) * upm_scale))
        elif fmt in (8, 9):  # PaintSweepGradient / Var — FWORD center
            if hasattr(paint, "centerX"):
                paint.centerX = otRound(paint.centerX * upm_scale)
            if hasattr(paint, "centerY"):
                paint.centerY = otRound(paint.centerY * upm_scale)
        else:
            # Catch-all for PaintScale/Rotate/Skew variants that use center coords
            # (FWORD int16 — must round)
            if hasattr(paint, "centerX"):
                paint.centerX = otRound(paint.centerX * upm_scale)
            if hasattr(paint, "centerY"):
                paint.centerY = otRound(paint.centerY * upm_scale)

        # Recurse into child paints (Format 1 = PaintColrLayers refs LayerList,
        # which is iterated separately below — skip it here to avoid double-scaling)
        if fmt == 1:
            return
        for attr in ("Paint", "SourcePaint", "BackdropPaint"):
            child = getattr(paint, attr, None)
            if child is not None:
                scale_paint(child)
        for child in getattr(paint, "Paints", []) or []:
            scale_paint(child)

    colr = colr_obj.table

    # Scale BaseGlyphList paint trees (inline only; LayerList refs handled below)
    if hasattr(colr, "BaseGlyphList") and colr.BaseGlyphList:
        for record in colr.BaseGlyphList.BaseGlyphPaintRecord:
            scale_paint(record.Paint)

    # Scale ALL LayerList entries (each is an independent paint node)
    if hasattr(colr, "LayerList") and colr.LayerList:
        for paint in colr.LayerList.Paint:
            scale_paint(paint)

    # Scale ClipList bounding boxes
    if hasattr(colr, "ClipList") and colr.ClipList:
        for clip in colr.ClipList.clips.values():
            clip.xMin = otRound(clip.xMin * upm_scale)
            clip.yMin = otRound(clip.yMin * upm_scale)
            clip.xMax = otRound(clip.xMax * upm_scale)
            clip.yMax = otRound(clip.yMax * upm_scale)


def _filter_colr_to_added_glyphs(
    base_font: TTFont,
    added_set: set[str],
) -> None:
    """Filter COLR BaseGlyphPaintRecord to only include added emoji glyphs.

    After merging the full COLRv1 table from the source emoji font, this
    removes records for codepoints we didn't add (either because they were
    skipped as existing, or because their glyph names conflicted with Sarasa).

    Args:
        base_font: Font with COLR table already merged in
        added_set: Set of emoji glyph names that were actually added
    """
    if "COLR" not in base_font:
        return
    colr = base_font["COLR"].table

    if hasattr(colr, "BaseGlyphList") and colr.BaseGlyphList:
        records = colr.BaseGlyphList.BaseGlyphPaintRecord
        before = len(records)
        colr.BaseGlyphList.BaseGlyphPaintRecord = [
            r for r in records if r.BaseGlyph in added_set
        ]
        removed = before - len(colr.BaseGlyphList.BaseGlyphPaintRecord)
        if removed:
            print(f"  Filtered {removed} COLR BaseGlyphPaintRecord entries not in added set")

    if hasattr(colr, "BaseGlyphRecord") and colr.BaseGlyphRecord:
        colr.BaseGlyphRecord = [
            r for r in colr.BaseGlyphRecord if r.BaseGlyph in added_set
        ]

    if hasattr(colr, "ClipList") and colr.ClipList:
        colr.ClipList.clips = {
            k: v for k, v in colr.ClipList.clips.items() if k in added_set
        }


def merge_emoji_colrv1(
    base_font_path: str,
    emoji_font_path: str,
    config: FontConfig,
    max_new_glyphs: int | None = None,
    priority_codepoints: set[int] | None = None,
    priority_sequences: list[tuple[int, ...]] | None = None,
    force_codepoints: set[int] | None = None,
) -> tuple[TTFont, list[dict]]:
    """Merge Noto COLRv1 color vector emoji into SarasaMonoTC.

    COLRv1 (OpenType Color Font Format Version 1) stores emoji as paint trees
    that reference geometry helper glyphs via PaintGlyph nodes.  This function:
    1. Copies emoji glyph stubs (empty glyf) + geometry dep outlines (scaled)
    2. Deep-copies and filters the COLR/CPAL tables
    3. Renames geometry dep glyphs when their names conflict with Sarasa

    Advantages over CBDT/CBLC (Color variant):
    - Scalable vector rendering (no pixelation at high DPI)
    - Smaller output file (~15 MB vs ~35 MB estimated)
    - Supported in Chrome/Chromium 98+ and modern terminals

    Args:
        base_font_path: Path to SarasaMonoTC-{Style}.ttf
        emoji_font_path: Path to Noto-COLRv1.ttf
        config: FontConfig object
        max_new_glyphs: If set, apply greedy codepoint-ordered selection to
            keep total new glyph slots (emoji stubs + geometry deps) within
            this limit.  Fixes browser garbling caused by oversized glyph tables.
        priority_codepoints: Codepoints always included before the greedy fill
            phase (e.g. commonly used dev/tooling emoji at higher codepoints).
        priority_sequences: Sequence codepoint tuples always attempted before the
            remaining-budget greedy fill for COLRv1 sequence glyphs.
        force_codepoints: BMP codepoints (≤ U+FFFF) that Sarasa already renders
            as monochrome glyphs.  These bypass skip_existing and get a renamed
            COLRv1 stub (e.g. uni2764 → uni2764_colrv1) so the cmap entry is
            redirected from Sarasa's monochrome glyph to the color vector version.
            Treated as Phase 0 in greedy selection (guaranteed priority).

    Returns:
        (merged_font, selection_records) where merged_font is the TTFont object
        (caller must call .save() and .close()) and selection_records is a list
        of dicts describing each selected emoji (empty when max_new_glyphs is None).
    """
    print(f"  Loading base font: {base_font_path}")
    base_font = TTFont(base_font_path, lazy=True, recalcBBoxes=False)
    print(f"  Loading emoji font: {emoji_font_path}")
    emoji_font = TTFont(emoji_font_path)

    if "COLR" not in emoji_font:
        raise ValueError(
            f"Emoji font '{emoji_font_path}' has no COLR table. "
            "COLRv1 variant requires Noto-COLRv1.ttf (from googlefonts/noto-emoji)."
        )

    # Step 1: detect widths
    half_width, full_width = detect_font_widths(base_font)
    emoji_width = half_width * config.emoji_width_multiplier
    print(f"  Detected widths — half: {half_width}, full: {full_width}, emoji: {emoji_width}")

    # Step 2: collect shared emoji metadata (single codepoints + sequences)
    emoji_entries = collect_emoji_entries(emoji_font, source_table_kind="COLRv1")
    emoji_cmap = {
        entry.codepoints[0]: entry.source_glyph
        for entry in emoji_entries
        if entry.kind == "single"
    }
    all_sequence_entries = [entry for entry in emoji_entries if entry.kind == "sequence"]
    print(
        f"  Emoji entries: {len(emoji_entries)} "
        f"(single: {len(emoji_cmap)}, sequence: {len(all_sequence_entries)})"
    )

    # Step 2.5: build rename map for forced BMP codepoints that conflict with Sarasa.
    # Must happen BEFORE skip_existing filter so emoji_cmap still contains them.
    # A forced codepoint like U+2764 (❤) has glyph name "uni2764" in BOTH Sarasa
    # and Noto-COLRv1.  We rename the COLRv1 copy to "uni2764_colrv1" so it can
    # coexist, and later redirect the cmap entry to the renamed stub.
    glyph_forced_rename: dict[str, str] = {}  # orig_name → colrv1_name
    if force_codepoints:
        base_glyph_names_early = set(base_font.getGlyphOrder())
        for cp in force_codepoints:
            if cp in emoji_cmap:
                orig_name = emoji_cmap[cp]
                if orig_name in base_glyph_names_early:
                    glyph_forced_rename[orig_name] = f"{orig_name}_colrv1"
        if glyph_forced_rename:
            print(
                f"  Forced BMP emoji with name conflicts: {len(glyph_forced_rename)} "
                f"(will be renamed: {sorted(glyph_forced_rename)[:5]})"
            )

    # Step 3: filter existing codepoints (skip_existing), but keep forced codepoints
    if config.skip_existing:
        base_cmap = base_font["cmap"].getBestCmap() or {}
        before = len(emoji_cmap)
        emoji_cmap = {
            cp: name for cp, name in emoji_cmap.items()
            if cp not in base_cmap or (force_codepoints is not None and cp in force_codepoints)
        }
        print(f"  Filtered existing codepoints: {before} → {len(emoji_cmap)}")

    if not emoji_cmap:
        print("  No new emoji to add.")
        emoji_font.close()
        return base_font, []

    # Step 3.5: greedy codepoint-ordered selection (COLRv1 glyph budget control)
    # Must happen after existing-codepoint filter but before dep collection,
    # because _select_colrv1_emoji_greedy also calls _collect_colrv1_paint_glyph_deps
    # internally to calculate per-emoji costs.
    selection_records: list[dict] = []
    if max_new_glyphs is not None:
        reserved_sequence_budget = _estimate_colrv1_priority_sequence_cost(
            all_sequence_entries,
            emoji_font,
            priority_sequences,
        )
        effective_single_budget = max_new_glyphs - reserved_sequence_budget
        if effective_single_budget <= 0:
            raise ValueError(
                f"COLRv1 max_new_glyphs={max_new_glyphs} is too small after reserving "
                f"{reserved_sequence_budget} slots for priority sequences"
            )
        if reserved_sequence_budget:
            print(
                f"  Reserving {reserved_sequence_budget} glyph slots for priority sequences "
                f"(single-emoji budget: {effective_single_budget}/{max_new_glyphs})"
            )
        # Trigger COLR decompilation once before greedy scan so that repeated
        # internal calls to _collect_colrv1_paint_glyph_deps are cache-warm.
        colr_table_pre = emoji_font["COLR"].table
        if hasattr(colr_table_pre, "BaseGlyphList") and colr_table_pre.BaseGlyphList:
            _ = colr_table_pre.BaseGlyphList.BaseGlyphPaintRecord
        # Combine priority + forced codepoints for Phase 0/1 guaranteed selection.
        # Forced codepoints use original names at this point (renames applied after),
        # so _collect_colrv1_paint_glyph_deps inside greedy can look them up in COLR.
        combined_priority = (priority_codepoints or set()) | (force_codepoints or set())
        emoji_cmap, selection_records = _select_colrv1_emoji_greedy(
            emoji_cmap, emoji_font, effective_single_budget,
            combined_priority if combined_priority else None,
        )
        if not emoji_cmap:
            print("  No emoji selected within glyph budget.")
            emoji_font.close()
            return base_font, []

    # Post-greedy: apply forced renames to emoji_cmap.
    # Now that greedy is done (which needed original names for COLR lookup),
    # rename BMP conflict glyphs: e.g. emoji_cmap[0x2764] = "uni2764_colrv1".
    if glyph_forced_rename:
        for cp in (force_codepoints or set()):
            if cp in emoji_cmap and emoji_cmap[cp] in glyph_forced_rename:
                emoji_cmap[cp] = glyph_forced_rename[emoji_cmap[cp]]
        # Sync glyph_name in selection_records for JSON output
        for rec in selection_records:
            if rec["glyph_name"] in glyph_forced_rename:
                rec["glyph_name"] = glyph_forced_rename[rec["glyph_name"]]

    # Calculate UPM scale: Noto-COLRv1.ttf uses UPM 1024, Sarasa uses UPM 1000.
    base_upm = base_font["head"].unitsPerEm
    emoji_upm = emoji_font["head"].unitsPerEm
    upm_scale = base_upm / emoji_upm
    if abs(upm_scale - 1.0) > 1e-6:
        print(f"  UPM scale: {emoji_upm} → {base_upm} (×{upm_scale:.4f})")

    # Step 4: build target_names (cmap values, excluding Sarasa name conflicts)
    base_existing_names = set(base_font.getGlyphOrder())
    target_names = {name for name in emoji_cmap.values() if name not in base_existing_names}
    name_conflicts = len({name for name in emoji_cmap.values()}) - len(target_names)

    # Step 5: collect geometry helper deps referenced by PaintGlyph nodes
    # Access COLR table to trigger decompilation before collection
    colr_table = emoji_font["COLR"].table
    if hasattr(colr_table, "BaseGlyphList") and colr_table.BaseGlyphList:
        _ = colr_table.BaseGlyphList.BaseGlyphPaintRecord  # trigger lazy load

    # Dep collection uses original glyph names (COLR records are keyed by original
    # name).  For forced-renamed emoji (e.g. uni2764_colrv1), map back to original
    # before the lookup so PaintGlyph trees for those emoji are also walked.
    if glyph_forced_rename:
        colrv1_to_orig = {v: k for k, v in glyph_forced_rename.items()}
        lookup_names = {colrv1_to_orig.get(n, n) for n in target_names}
    else:
        lookup_names = target_names
    geometry_deps = _collect_colrv1_paint_glyph_deps(emoji_font, lookup_names)
    geometry_deps -= lookup_names  # avoid double-counting emoji used as deps

    # Step 5.5: greedily add sequence glyphs within the remaining COLRv1 budget.
    selected_sequence_entries: list[EmojiEntry] = []
    selected_sequence_names: set[str] = set()
    selected_sequence_deps: set[str] = set()
    if max_new_glyphs is not None and all_sequence_entries:
        used_cost = len(target_names) + len(geometry_deps)
        remaining_budget = max_new_glyphs - used_cost
        selected_sequence_entries, selected_sequence_deps = _select_colrv1_sequences_greedy(
            all_sequence_entries,
            emoji_font,
            remaining_budget,
            lookup_names,
            geometry_deps,
            priority_sequences=priority_sequences,
        )
        selected_sequence_names = {entry.source_glyph for entry in selected_sequence_entries}
        if selected_sequence_entries:
            print(
                f"  Sequence selection: {len(selected_sequence_entries)}/{len(all_sequence_entries)} "
                f"selected, extra glyph cost: {len(selected_sequence_names) + len(selected_sequence_deps)}/{remaining_budget}"
            )

    geometry_deps |= selected_sequence_deps
    print(
        f"  Target emoji: {len(target_names)}, geometry deps: {len(geometry_deps)}, "
        f"name conflicts (skipped): {name_conflicts}"
    )

    # Step 6: rename geometry deps whose names conflict with Sarasa glyph names
    rename_map: dict[str, str] = {}
    for name in geometry_deps:
        if name in base_existing_names:
            rename_map[name] = f"{name}_colrv1"
    if rename_map:
        print(f"  Renaming {len(rename_map)} conflicting geometry dep(s): {sorted(rename_map)[:5]}")

    sequence_rename_map: dict[str, str] = {}
    for name in selected_sequence_names:
        if name in base_existing_names:
            sequence_rename_map[name] = f"{name}_colrv1_seq"
    if sequence_rename_map:
        print(
            f"  Renaming {len(sequence_rename_map)} conflicting sequence glyph(s): "
            f"{sorted(sequence_rename_map)[:5]}"
        )

    # Build ordered lists: geometry deps first (referenced by paint trees), then emoji
    geometry_deps_orig = sorted(geometry_deps)         # original names in emoji font
    geometry_deps_final = [rename_map.get(n, n) for n in geometry_deps_orig]
    sequence_glyphs_orig = sorted(selected_sequence_names)
    sequence_glyphs_final = [sequence_rename_map.get(n, n) for n in sequence_glyphs_orig]
    emoji_glyphs_list = sorted(target_names) + sequence_glyphs_final
    emoji_glyphs_to_add = geometry_deps_final + emoji_glyphs_list

    print(f"  Glyphs to add: {len(emoji_glyphs_to_add)} "
          f"({len(geometry_deps_final)} geometry deps + {len(emoji_glyphs_list)} emoji)")

    # Step 7: deep copy COLR + CPAL (COLR already decompiled above)
    print("  Copying COLR/CPAL tables...")
    colr_copy = copy.deepcopy(emoji_font["COLR"])
    cpal_copy = copy.deepcopy(emoji_font["CPAL"]) if "CPAL" in emoji_font else None

    # Apply rename_map so PaintGlyph refs point to the renamed geometry dep names.
    # Must cover both BaseGlyphList paint trees AND LayerList entries, because
    # PaintColrLayers (Format=1) — the dominant format in Noto-COLRv1 — stores
    # its paint operations in the shared LayerList, not inline in the record.
    if rename_map:
        colr_table_copy = colr_copy.table
        if hasattr(colr_table_copy, "BaseGlyphList") and colr_table_copy.BaseGlyphList:
            for record in colr_table_copy.BaseGlyphList.BaseGlyphPaintRecord:
                _apply_colrv1_rename(record.Paint, rename_map)
        if hasattr(colr_table_copy, "LayerList") and colr_table_copy.LayerList:
            for layer_paint in colr_table_copy.LayerList.Paint:
                _apply_colrv1_rename(layer_paint, rename_map)

    # For forced BMP emoji, also rename the BaseGlyph field itself in COLR records.
    # e.g. BaseGlyph "uni2764" → "uni2764_colrv1" so the renderer maps the cmap
    # entry (which _update_cmap will redirect to "uni2764_colrv1") to this record.
    if glyph_forced_rename:
        colr_table_copy = colr_copy.table
        if hasattr(colr_table_copy, "BaseGlyphList") and colr_table_copy.BaseGlyphList:
            for record in colr_table_copy.BaseGlyphList.BaseGlyphPaintRecord:
                if record.BaseGlyph in glyph_forced_rename:
                    record.BaseGlyph = glyph_forced_rename[record.BaseGlyph]
    if sequence_rename_map:
        colr_table_copy = colr_copy.table
        if hasattr(colr_table_copy, "BaseGlyphList") and colr_table_copy.BaseGlyphList:
            for record in colr_table_copy.BaseGlyphList.BaseGlyphPaintRecord:
                if record.BaseGlyph in sequence_rename_map:
                    record.BaseGlyph = sequence_rename_map[record.BaseGlyph]

    # Step 7.5: scale font-unit coords in COLR by upm_scale.
    # PaintTransform dx/dy, PaintTranslate dx/dy, gradient control points, and
    # ClipBox coordinates are all in source-font units (Noto UPM=1024).  After
    # scaling glyph outlines (Step 10), the same ratio must be applied to every
    # font-unit value in the paint tree so that transforms position correctly in
    # the target UPM (Sarasa UPM=1000).  Unitless values (scale ratios, angles)
    # are left unchanged.
    if abs(upm_scale - 1.0) > 1e-6:
        _scale_colrv1_paint_coords(colr_copy, upm_scale)

    # Step 8: access base_glyf BEFORE setGlyphOrder (OTS ordering constraint —
    # prevents flag-encoding change that OTS rejects; see merge_emoji() comment)
    if "glyf" in base_font:
        base_glyf = base_font["glyf"]

    # Step 9: extend glyph order
    original_order = base_font.getGlyphOrder()
    new_order = original_order + emoji_glyphs_to_add
    base_font.setGlyphOrder(new_order)

    # Step 10: copy geometry dep outlines (scaled) + add empty emoji stubs
    if "glyf" in base_font:
        emoji_glyf = emoji_font.get("glyf")
        geo_copied = 0
        for orig_name, final_name in zip(geometry_deps_orig, geometry_deps_final):
            if final_name not in base_glyf.glyphs:
                src = emoji_glyf.glyphs.get(orig_name) if emoji_glyf else None
                if src is not None:
                    src.expand(emoji_glyf)
                    glyph_copy = copy.deepcopy(src)
                    _scale_glyph(glyph_copy, upm_scale)
                    base_glyf[final_name] = glyph_copy
                    geo_copied += 1
                else:
                    empty = TTGlyph()
                    empty.numberOfContours = 0
                    base_glyf[final_name] = empty

        for glyph_name in emoji_glyphs_list:
            if glyph_name not in base_glyf.glyphs:
                empty = TTGlyph()
                empty.numberOfContours = 0
                base_glyf[glyph_name] = empty

        print(f"  Copied {geo_copied} geometry dep outlines (scaled ×{upm_scale:.4f}), "
              f"added {len(emoji_glyphs_list)} emoji stubs")

    # Step 11: update hmtx/vmtx
    # IMPORTANT: access vmtx BEFORE updating maxp.numGlyphs (same ordering as merge_emoji)
    base_hmtx = base_font["hmtx"]
    geometry_deps_final_set = set(geometry_deps_final)
    from fontTools.misc.roundTools import otRound

    # Preserve source metrics for geometry deps.
    #
    # Although these glyphs are internal helpers (not directly mapped in cmap),
    # Chromium's COLRv1 PaintGlyph rendering appears to depend on the helper
    # glyph metrics/phantom-point geometry matching the source font.  Setting
    # all geometry deps to (0, 0) shifts high-scale transformed glyphs such as
    # 🟡/🟢 far enough that they clip incorrectly in the browser.
    emoji_hmtx = emoji_font["hmtx"]
    geometry_hmetrics: dict[str, tuple[int, int]] = {}
    for orig_name, final_name in zip(geometry_deps_orig, geometry_deps_final):
        if orig_name in emoji_hmtx.metrics:
            adv, lsb = emoji_hmtx.metrics[orig_name]
            geometry_hmetrics[final_name] = (
                otRound(adv * upm_scale),
                otRound(lsb * upm_scale),
            )
        else:
            geometry_hmetrics[final_name] = (0, 0)

    for glyph_name in emoji_glyphs_to_add:
        if glyph_name not in base_hmtx.metrics:
            if glyph_name in geometry_deps_final_set:
                base_hmtx.metrics[glyph_name] = geometry_hmetrics.get(glyph_name, (0, 0))
            else:
                base_hmtx.metrics[glyph_name] = (emoji_width, 0)

    if "vmtx" in base_font:
        base_vmtx = base_font["vmtx"]
        emoji_vmtx = emoji_font["vmtx"] if "vmtx" in emoji_font else None
        for glyph_name in emoji_glyphs_to_add:
            if glyph_name not in base_vmtx.metrics:
                if glyph_name in geometry_deps_final_set and emoji_vmtx is not None:
                    orig_name = next(
                        (src for src, dst in zip(geometry_deps_orig, geometry_deps_final) if dst == glyph_name),
                        None,
                    )
                    if orig_name is not None and orig_name in emoji_vmtx.metrics:
                        adv, tsb = emoji_vmtx.metrics[orig_name]
                        base_vmtx.metrics[glyph_name] = (
                            otRound(adv * upm_scale),
                            otRound(tsb * upm_scale),
                        )
                    else:
                        base_vmtx.metrics[glyph_name] = (0, 0)
                else:
                    base_vmtx.metrics[glyph_name] = (emoji_width, 0)

    # Update maxp AFTER all table accesses (avoids vmtx decompile byte-count mismatch)
    base_font["maxp"].numGlyphs = len(new_order)

    # Step 12: attach COLR/CPAL and filter to added emoji glyphs
    base_font["COLR"] = colr_copy
    if cpal_copy is not None:
        base_font["CPAL"] = cpal_copy
    added_emoji_set = set(emoji_glyphs_list)
    _filter_colr_to_added_glyphs(base_font, added_emoji_set)

    # Step 13: update cmap.
    # force_codepoints allows overwriting existing BMP entries so that e.g.
    # U+2764 → uni2764_colrv1 instead of Sarasa's original monochrome uni2764.
    updated = _update_cmap(base_font, emoji_cmap, added_emoji_set, force_codepoints)
    print(f"  cmap entries added: {updated}")

    if selected_sequence_entries:
        merged_cmap = base_font["cmap"].getBestCmap() or {}
        gsub_sequence_entries = [
            EmojiEntry(
                codepoints=entry.codepoints,
                source_glyph=sequence_rename_map.get(entry.source_glyph, entry.source_glyph),
                kind=entry.kind,
                source_table_kind=entry.source_table_kind,
            )
            for entry in selected_sequence_entries
        ]
        ligature_map = _build_sequence_ligature_map(gsub_sequence_entries, merged_cmap, added_emoji_set)
        appended_sequences = _append_ligature_lookup_to_gsub(base_font, ligature_map)
        if appended_sequences:
            print(f"  GSUB sequence ligatures appended: {appended_sequences}")

    # Step 14: update hhea and OS/2
    if "hhea" in base_font:
        base_font["hhea"].advanceWidthMax = max(
            base_font["hhea"].advanceWidthMax, emoji_width
        )
        base_font["hhea"].numberOfHMetrics = len(base_hmtx.metrics)

    from .utils import merge_os2_ranges
    merge_os2_ranges(base_font, emoji_font)

    _strip_mac_name_records(base_font)

    emoji_font.close()
    print(f"  Total glyphs after merge: {len(base_font.getGlyphOrder())}")
    return base_font, selection_records
