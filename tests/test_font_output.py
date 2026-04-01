"""Integration tests for built font output.

These tests verify correctness of the merged fonts produced by build.py.
All tests skip gracefully if the output fonts have not been built yet.

Run after building:
    uv run python build.py --styles Regular
    uv run python build.py --lite --styles Regular
    pytest tests/test_font_output.py -v
"""

from pathlib import Path

import pytest
from fontTools.ttLib import TTFont
from fontTools.misc.roundTools import otRound

_KEY_CODEPOINTS = [
    (0x1F600, "😀"),
    (0x1F525, "🔥"),
    (0x4E00, "一"),
]

# Sarasa Mono TC Regular + NotoColorEmoji: well over 56 000 glyphs
_MIN_COLOR_GLYPHS = 56_000
# Sarasa + emoji outlines only: slightly more than Sarasa alone (~3 800 emoji)
_MIN_LITE_GLYPHS = 5_000
_STYLE_MATRIX = ("Regular", "Italic", "Bold", "BoldItalic")
_ROOT = Path(__file__).parent.parent
_LITE_POC_FLAGS = [
    ("US", (0x1F1FA, 0x1F1F8)),
    ("JP", (0x1F1EF, 0x1F1F5)),
    ("TW", (0x1F1F9, 0x1F1FC)),
    ("CN", (0x1F1E8, 0x1F1F3)),
    ("GB", (0x1F1EC, 0x1F1E7)),
    ("CA", (0x1F1E8, 0x1F1E6)),
    ("SG", (0x1F1F8, 0x1F1EC)),
    ("AU", (0x1F1E6, 0x1F1FA)),
    ("TH", (0x1F1F9, 0x1F1ED)),
    ("PH", (0x1F1F5, 0x1F1ED)),
    ("VN", (0x1F1FB, 0x1F1F3)),
    ("NZ", (0x1F1F3, 0x1F1FF)),
    ("KR", (0x1F1F0, 0x1F1F7)),
    ("HK", (0x1F1ED, 0x1F1F0)),
]
_REGIONAL_INDICATOR_START = 0x1F1E6
_REGIONAL_INDICATOR_END = 0x1F1FF


def _has_ligature_sequence(font, codepoints: tuple[int, ...]) -> bool:
    """Return True when GSUB contains a ligature rule for the given codepoints."""
    if "GSUB" not in font:
        return False

    cmap = font["cmap"].getBestCmap() or {}
    expected_components = []
    for cp in codepoints:
        glyph_name = cmap.get(cp)
        if glyph_name is None:
            return False
        expected_components.append(glyph_name)

    expected_components = tuple(expected_components)
    for lookup in font["GSUB"].table.LookupList.Lookup:
        if lookup.LookupType != 4:
            continue
        for subtable in lookup.SubTable:
            ligatures = getattr(subtable, "ligatures", None) or {}
            lig_list = ligatures.get(expected_components[0], [])
            for ligature in lig_list:
                components = (expected_components[0], *ligature.Component)
                if components == expected_components:
                    return True

    return False


def _resolve_ligature_output(font, codepoints: tuple[int, ...]) -> str | None:
    """Return the ligature output glyph name for the given codepoint sequence."""
    if "GSUB" not in font:
        return None

    cmap = font["cmap"].getBestCmap() or {}
    expected_components = []
    for cp in codepoints:
        glyph_name = cmap.get(cp)
        if glyph_name is None:
            return None
        expected_components.append(glyph_name)

    expected_components = tuple(expected_components)
    for lookup in font["GSUB"].table.LookupList.Lookup:
        if lookup.LookupType != 4:
            continue
        for subtable in lookup.SubTable:
            ligatures = getattr(subtable, "ligatures", None) or {}
            lig_list = ligatures.get(expected_components[0], [])
            for ligature in lig_list:
                components = (expected_components[0], *ligature.Component)
                if components == expected_components:
                    return ligature.LigGlyph

    return None


def _collect_ri_flag_ligatures(font) -> dict[tuple[int, int], str]:
    """Return all GSUB ligatures whose input is a 2-codepoint RI flag sequence."""
    if "GSUB" not in font:
        return {}

    cmap = font["cmap"].getBestCmap() or {}
    glyph_to_cp = {glyph_name: cp for cp, glyph_name in cmap.items()}
    result: dict[tuple[int, int], str] = {}

    for lookup in font["GSUB"].table.LookupList.Lookup:
        if lookup.LookupType != 4:
            continue
        for subtable in lookup.SubTable:
            ligatures = getattr(subtable, "ligatures", None) or {}
            for first_glyph, lig_list in ligatures.items():
                first_cp = glyph_to_cp.get(first_glyph)
                if first_cp is None:
                    continue
                for ligature in lig_list:
                    cps = [first_cp]
                    for component_name in ligature.Component:
                        cp = glyph_to_cp.get(component_name)
                        if cp is None:
                            cps = []
                            break
                        cps.append(cp)
                    if len(cps) != 2:
                        continue
                    if not all(_REGIONAL_INDICATOR_START <= cp <= _REGIONAL_INDICATOR_END for cp in cps):
                        continue
                    result[(cps[0], cps[1])] = ligature.LigGlyph

    return result


def _load_output_font(variant_dir: str, family_prefix: str, style: str) -> TTFont:
    """Open a built output font for a specific variant/style, or skip."""
    path = _ROOT / "output" / variant_dir / f"{family_prefix}-{style}.ttf"
    if not path.exists():
        pytest.skip(f"Output font not found: {path}")
    return TTFont(str(path))


# ---------------------------------------------------------------------------
# Color variant (CBDT/CBLC)
# ---------------------------------------------------------------------------

class TestColorOutput:
    def test_has_cbdt_and_cblc(self, output_color_regular):
        """Color variant must contain CBDT and CBLC tables."""
        assert "CBDT" in output_color_regular, "Missing CBDT table"
        assert "CBLC" in output_color_regular, "Missing CBLC table"

    def test_has_glyf_table(self, output_color_regular):
        """Color variant must retain Sarasa's glyf table."""
        assert "glyf" in output_color_regular

    def test_key_codepoints_present(self, output_color_regular):
        """Critical codepoints must be in cmap."""
        cmap = output_color_regular["cmap"].getBestCmap() or {}
        for cp, name in _KEY_CODEPOINTS:
            assert cp in cmap, f"Missing U+{cp:04X} {name}"

    def test_emoji_glyph_width_is_double_halfwidth(self, output_color_regular):
        """Emoji advance width must equal 2× the half-width (full-width)."""
        cmap = output_color_regular["cmap"].getBestCmap() or {}
        hmtx = output_color_regular["hmtx"]

        # Detect half-width from known ASCII glyph
        assert 0x0041 in cmap, "Missing 'A' in cmap"
        half_width, _ = hmtx[cmap[0x0041]]
        expected_emoji_width = half_width * 2

        # Check all key emoji codepoints
        for cp, char in _KEY_CODEPOINTS:
            if cp == 0x4E00:
                continue  # CJK character, not emoji width
            glyph_name = cmap[cp]
            actual_width, _ = hmtx[glyph_name]
            assert actual_width == expected_emoji_width, (
                f"U+{cp:04X} {char}: expected width {expected_emoji_width}, "
                f"got {actual_width}"
            )

    def test_glyph_count_reasonable(self, output_color_regular):
        """Total glyph count must exceed the minimum expected after merge."""
        count = len(output_color_regular.getGlyphOrder())
        assert count > _MIN_COLOR_GLYPHS, (
            f"Expected >{_MIN_COLOR_GLYPHS} glyphs, got {count}"
        )

    def test_no_mac_platform_name_records(self, output_color_regular):
        """Mac platform (platformID=1) name records must be stripped."""
        mac_records = [
            r for r in output_color_regular["name"].names if r.platformID == 1
        ]
        assert mac_records == [], (
            f"Found {len(mac_records)} Mac platform name records; should be 0"
        )

    def test_family_name_contains_emoji(self, output_color_regular):
        """Font family name must include 'Emoji'."""
        name_table = output_color_regular["name"]
        family = name_table.getBestFamilyName() or ""
        assert "Emoji" in family, f"Family name '{family}' does not contain 'Emoji'"

    def test_post_format_2_when_force_codepoints(self, output_color_regular):
        """Color variant with force_color_codepoints must use post format 2.0.

        Sarasa source uses post format 3.0 (no stored names).  When forced
        BMP renames are active (e.g. uni2764 → uni2764_color), merge_emoji
        upgrades post to format 2.0 so that glyph names survive save/reload.
        This test verifies the upgrade persisted into the built output file.
        """
        assert output_color_regular["post"].formatType == 2.0, (
            "post table must be format 2.0 when force_color_codepoints is active; "
            "format 3.0 causes _color-suffixed glyph names to be lost on reload"
        )

    def test_forced_bmp_codepoints_use_color_glyph(self, output_color_regular):
        """Forced BMP codepoints must point to _color-suffixed glyphs in cmap.

        Verifies that the save/reload cycle preserves the renamed glyphs so
        that e.g. U+2764 ❤ maps to 'uni2764_color' (CBDT bitmap) rather than
        reverting to Sarasa's original monochrome 'uni2764'.
        """
        cmap = output_color_regular["cmap"].getBestCmap() or {}
        # Default force_color_codepoints from config.yaml
        forced = {
            0x2764: "❤",
            0x2B50: "⭐",
            0x26A0: "⚠",
            0x263A: "☺",
            0x26A1: "⚡",
        }
        for cp, char in forced.items():
            glyph = cmap.get(cp, "")
            assert "_color" in glyph or glyph == "smileface_color", (
                f"U+{cp:04X} {char}: expected a '_color' glyph, got {glyph!r}. "
                "post format 3.0 causes the renamed glyph to revert to the "
                "base name on reload."
            )

    def test_has_sequence_gsub_for_zwj_skin_tone_and_flag(self, output_color_regular):
        """Color output must carry representative v2.0 sequence ligatures in GSUB."""
        assert _has_ligature_sequence(output_color_regular, (0x1F469, 0x200D, 0x1F4BB)), (
            "Missing 👩‍💻 ZWJ ligature in Color GSUB"
        )
        assert _has_ligature_sequence(output_color_regular, (0x1F44B, 0x1F3FB)), (
            "Missing 👋🏻 skin-tone ligature in Color GSUB"
        )
        assert _has_ligature_sequence(output_color_regular, (0x1F1FA, 0x1F1F8)), (
            "Missing 🇺🇸 flag ligature in Color GSUB"
        )

    @pytest.mark.parametrize("style", _STYLE_MATRIX)
    def test_all_styles_have_sequence_gsub(self, style):
        """All built Color styles should carry representative v2.0 sequence ligatures."""
        font = _load_output_font("fonts", "SarasaMonoTCEmoji", style)
        try:
            assert _has_ligature_sequence(font, (0x1F469, 0x200D, 0x1F4BB))
            assert _has_ligature_sequence(font, (0x1F44B, 0x1F3FB))
            assert _has_ligature_sequence(font, (0x1F1FA, 0x1F1F8))
        finally:
            font.close()


# ---------------------------------------------------------------------------
# Lite variant (glyf TrueType outlines)
# ---------------------------------------------------------------------------

class TestLiteOutput:
    def test_has_glyf_no_cbdt(self, output_lite_regular):
        """Lite variant must have glyf but must NOT have CBDT/CBLC."""
        assert "glyf" in output_lite_regular, "Missing glyf table"
        assert "CBDT" not in output_lite_regular, "Lite variant must not have CBDT"
        assert "CBLC" not in output_lite_regular, "Lite variant must not have CBLC"

    def test_key_codepoints_present(self, output_lite_regular):
        """Critical codepoints must be in cmap."""
        cmap = output_lite_regular["cmap"].getBestCmap() or {}
        for cp, name in _KEY_CODEPOINTS:
            assert cp in cmap, f"Missing U+{cp:04X} {name}"

    def test_emoji_glyph_width_is_double_halfwidth(self, output_lite_regular):
        """Emoji advance width must equal 2× the half-width."""
        cmap = output_lite_regular["cmap"].getBestCmap() or {}
        hmtx = output_lite_regular["hmtx"]

        assert 0x0041 in cmap, "Missing 'A' in cmap"
        half_width, _ = hmtx[cmap[0x0041]]
        expected_emoji_width = half_width * 2

        for cp, char in _KEY_CODEPOINTS:
            if cp == 0x4E00:
                continue
            glyph_name = cmap[cp]
            actual_width, _ = hmtx[glyph_name]
            assert actual_width == expected_emoji_width, (
                f"U+{cp:04X} {char}: expected width {expected_emoji_width}, "
                f"got {actual_width}"
            )

    def test_emoji_bbox_within_sarasa_line_metrics(self, output_lite_regular):
        """Emoji glyph bbox must fit within Sarasa's ascender/descender range.

        After UPM scaling (2048→1000), emoji should not exceed Sarasa's
        vertical metrics.  Sarasa Regular: ascender=965, descender=-215.
        We use a ±20% tolerance to accommodate edge cases.
        """
        cmap = output_lite_regular["cmap"].getBestCmap() or {}
        glyf = output_lite_regular["glyf"]
        os2 = output_lite_regular["OS/2"]
        ascender = os2.sTypoAscender
        descender = os2.sTypoDescender
        tolerance = 0.2

        failures = []
        for cp, char in [(0x1F600, "😀"), (0x1F525, "🔥")]:
            if cp not in cmap:
                continue
            glyph_name = cmap[cp]
            glyph = glyf[glyph_name]
            if glyph is None or glyph.numberOfContours == 0:
                continue
            if glyph.yMax > ascender * (1 + tolerance):
                failures.append(
                    f"U+{cp:04X} {char}: yMax={glyph.yMax} > ascender={ascender}×{1+tolerance}"
                )
            if glyph.yMin < descender * (1 + tolerance):
                failures.append(
                    f"U+{cp:04X} {char}: yMin={glyph.yMin} < descender={descender}×{1+tolerance}"
                )

        assert not failures, "\n".join(failures)

    def test_glyph_count_reasonable(self, output_lite_regular):
        """Total glyph count must exceed the minimum after merge."""
        count = len(output_lite_regular.getGlyphOrder())
        assert count > _MIN_LITE_GLYPHS, (
            f"Expected >{_MIN_LITE_GLYPHS} glyphs, got {count}"
        )

    def test_no_mac_platform_name_records(self, output_lite_regular):
        """Mac platform (platformID=1) name records must be stripped."""
        mac_records = [
            r for r in output_lite_regular["name"].names if r.platformID == 1
        ]
        assert mac_records == [], (
            f"Found {len(mac_records)} Mac platform name records; should be 0"
        )

    def test_family_name_contains_emoji_lite(self, output_lite_regular):
        """Font family name must include 'EmojiLite' or 'Emoji Lite'."""
        name_table = output_lite_regular["name"]
        family = name_table.getBestFamilyName() or ""
        assert "Emoji" in family and "Lite" in family, (
            f"Family name '{family}' does not indicate Lite variant"
        )

    @pytest.mark.parametrize(("label", "codepoints"), _LITE_POC_FLAGS)
    def test_poc_flags_use_custom_components(self, output_lite_regular, label, codepoints):
        """Representative Lite flags should resolve to the custom template + letters."""
        glyph_name = _resolve_ligature_output(output_lite_regular, codepoints)
        assert glyph_name, f"Missing ligature output for {label}"

        glyf = output_lite_regular["glyf"]
        glyph = glyf[glyph_name]
        glyph.expand(glyf)
        component_names = [comp.glyphName for comp in getattr(glyph, "components", None) or []]
        assert len(component_names) == 3, (
            f"{label}: expected 3 components, got {component_names}"
        )
        assert component_names[0] == "poc_lite_flag_template", (
            f"{label}: expected PoC flag template, got {component_names}"
        )
        assert component_names[1].startswith("poc_lite_letter."), (
            f"{label}: expected custom left letter, got {component_names}"
        )
        assert component_names[2].startswith("poc_lite_letter."), (
            f"{label}: expected custom right letter, got {component_names}"
        )

    def test_all_ri_flags_use_custom_components(self, output_lite_regular):
        """All standard RI-pair flag ligatures should use the custom Lite flag system."""
        ligatures = _collect_ri_flag_ligatures(output_lite_regular)
        assert ligatures, "Expected at least one RI-pair flag ligature in Lite output"
        glyf = output_lite_regular["glyf"]
        for codepoints, glyph_name in ligatures.items():
            glyph = glyf[glyph_name]
            glyph.expand(glyf)
            component_names = [comp.glyphName for comp in getattr(glyph, "components", None) or []]
            assert len(component_names) == 3, (
                f"{codepoints}: expected 3 custom flag components, got {component_names}"
            )
            assert component_names[0] == "poc_lite_flag_template", (
                f"{codepoints}: expected PoC template, got {component_names}"
            )
            assert component_names[1].startswith("poc_lite_letter."), (
                f"{codepoints}: expected custom left letter, got {component_names}"
            )
            assert component_names[2].startswith("poc_lite_letter."), (
                f"{codepoints}: expected custom right letter, got {component_names}"
            )

    def test_has_sequence_gsub_for_zwj_skin_tone_and_flag(self, output_lite_regular):
        """Lite output must carry representative v2.0 sequence ligatures in GSUB."""
        assert _has_ligature_sequence(output_lite_regular, (0x1F469, 0x200D, 0x1F4BB)), (
            "Missing 👩‍💻 ZWJ ligature in Lite GSUB"
        )
        assert _has_ligature_sequence(output_lite_regular, (0x1F44B, 0x1F3FB)), (
            "Missing 👋🏻 skin-tone ligature in Lite GSUB"
        )
        assert _has_ligature_sequence(output_lite_regular, (0x1F1FA, 0x1F1F8)), (
            "Missing 🇺🇸 flag ligature in Lite GSUB"
        )

    def test_forced_bmp_codepoints_use_lite_glyph(self, output_lite_regular):
        """Lite variant should override configured BMP symbols with Noto outlines.

        These codepoints already exist in Sarasa. Lite now follows the same
        allowlist as Color/COLRv1, renaming conflicting glyphs with a `_lite`
        suffix so the Noto Emoji outline survives save/reload.
        """
        cmap = output_lite_regular["cmap"].getBestCmap() or {}
        expected = {
            0x2328: "uni2328_lite",
            0x274C: "uni274C_lite",
            0x2764: "redHeart",
            0x2B06: "arrowup_lite",
            0x2B07: "arrowdown_lite",
            0x2B50: "uni2B50_lite",
            0x26A0: "warning",
            0x263A: "smileface_lite",
            0x26A1: "highVoltage",
        }
        for cp, glyph_name in expected.items():
            glyph = cmap.get(cp, "")
            assert glyph == glyph_name, (
                f"U+{cp:04X}: expected {glyph_name!r}, got {glyph!r}"
            )

    @pytest.mark.parametrize("style", _STYLE_MATRIX)
    def test_all_styles_have_sequence_gsub(self, style):
        """All built Lite styles should carry representative v2.0 sequence ligatures."""
        font = _load_output_font("fonts-lite", "SarasaMonoTCEmojiLite", style)
        try:
            assert _has_ligature_sequence(font, (0x1F469, 0x200D, 0x1F4BB))
            assert _has_ligature_sequence(font, (0x1F44B, 0x1F3FB))
            assert _has_ligature_sequence(font, (0x1F1FA, 0x1F1F8))
        finally:
            font.close()


# ---------------------------------------------------------------------------
# COLRv1 variant (color vector)
# ---------------------------------------------------------------------------

_MIN_COLRV1_GLYPHS = 5_000


class TestCOLRv1Output:
    def test_has_colr_and_cpal(self, output_colrv1_regular):
        """COLRv1 variant must contain COLR and CPAL tables."""
        assert "COLR" in output_colrv1_regular, "Missing COLR table"
        assert "CPAL" in output_colrv1_regular, "Missing CPAL table"

    def test_has_no_cbdt_cblc(self, output_colrv1_regular):
        """COLRv1 variant must NOT have CBDT/CBLC tables."""
        assert "CBDT" not in output_colrv1_regular, "COLRv1 variant must not have CBDT"
        assert "CBLC" not in output_colrv1_regular, "COLRv1 variant must not have CBLC"

    def test_has_glyf_table(self, output_colrv1_regular):
        """COLRv1 variant must retain Sarasa's glyf table."""
        assert "glyf" in output_colrv1_regular

    def test_key_codepoints_present(self, output_colrv1_regular):
        """Critical codepoints must be in cmap."""
        cmap = output_colrv1_regular["cmap"].getBestCmap() or {}
        for cp, name in _KEY_CODEPOINTS:
            assert cp in cmap, f"Missing U+{cp:04X} {name}"

    def test_emoji_glyph_width_is_double_halfwidth(self, output_colrv1_regular):
        """Emoji advance width must equal 2× the half-width (full-width)."""
        cmap = output_colrv1_regular["cmap"].getBestCmap() or {}
        hmtx = output_colrv1_regular["hmtx"]

        assert 0x0041 in cmap, "Missing 'A' in cmap"
        half_width, _ = hmtx[cmap[0x0041]]
        expected_emoji_width = half_width * 2

        for cp, char in _KEY_CODEPOINTS:
            if cp == 0x4E00:
                continue
            glyph_name = cmap[cp]
            actual_width, _ = hmtx[glyph_name]
            assert actual_width == expected_emoji_width, (
                f"U+{cp:04X} {char}: expected width {expected_emoji_width}, "
                f"got {actual_width}"
            )

    def test_colr_base_glyph_records_present(self, output_colrv1_regular):
        """COLR BaseGlyphPaintRecord must contain at least one entry."""
        colr = output_colrv1_regular["COLR"].table
        assert hasattr(colr, "BaseGlyphList") and colr.BaseGlyphList, "Missing BaseGlyphList"
        records = colr.BaseGlyphList.BaseGlyphPaintRecord
        assert len(records) > 0, "COLR BaseGlyphPaintRecord is empty"

    def test_emoji_glyph_has_colr_record(self, output_colrv1_regular):
        """😀 U+1F600 glyph must have a COLR paint record."""
        cmap = output_colrv1_regular["cmap"].getBestCmap() or {}
        assert 0x1F600 in cmap, "Missing 😀 U+1F600 in cmap"
        glyph_name = cmap[0x1F600]
        colr = output_colrv1_regular["COLR"].table
        record_names = {r.BaseGlyph for r in colr.BaseGlyphList.BaseGlyphPaintRecord}
        assert glyph_name in record_names, (
            f"Glyph '{glyph_name}' for U+1F600 has no COLR paint record"
        )

    def test_glyph_count_reasonable(self, output_colrv1_regular):
        """Total glyph count must exceed the minimum after merge."""
        count = len(output_colrv1_regular.getGlyphOrder())
        assert count > _MIN_COLRV1_GLYPHS, (
            f"Expected >{_MIN_COLRV1_GLYPHS} glyphs, got {count}"
        )

    def test_no_mac_platform_name_records(self, output_colrv1_regular):
        """Mac platform (platformID=1) name records must be stripped."""
        mac_records = [
            r for r in output_colrv1_regular["name"].names if r.platformID == 1
        ]
        assert mac_records == [], (
            f"Found {len(mac_records)} Mac platform name records; should be 0"
        )

    def test_family_name_contains_colrv1(self, output_colrv1_regular):
        """Font family name must indicate the COLRv1 variant."""
        name_table = output_colrv1_regular["name"]
        family = name_table.getBestFamilyName() or ""
        assert "COLRv1" in family or "colrv1" in family.lower(), (
            f"Family name '{family}' does not indicate COLRv1 variant"
        )

    def test_has_sequence_gsub_for_zwj_skin_tone_and_flag(self, output_colrv1_regular):
        """COLRv1 output should carry representative v2.0 sequence ligatures when selected."""
        assert _has_ligature_sequence(output_colrv1_regular, (0x1F469, 0x200D, 0x1F4BB)), (
            "Missing 👩‍💻 ZWJ ligature in COLRv1 GSUB"
        )
        assert _has_ligature_sequence(output_colrv1_regular, (0x1F44B, 0x1F3FB)), (
            "Missing 👋🏻 skin-tone ligature in COLRv1 GSUB"
        )
        assert _has_ligature_sequence(output_colrv1_regular, (0x1F1FA, 0x1F1F8)), (
            "Missing 🇺🇸 flag ligature in COLRv1 GSUB"
        )

    @pytest.mark.parametrize("style", _STYLE_MATRIX)
    def test_all_styles_have_sequence_gsub(self, style):
        """All built COLRv1 styles should carry the representative priority sequences."""
        font = _load_output_font("fonts-colrv1", "SarasaMonoTCEmojiCOLRv1", style)
        try:
            assert _has_ligature_sequence(font, (0x1F469, 0x200D, 0x1F4BB))
            assert _has_ligature_sequence(font, (0x1F44B, 0x1F3FB))
            assert _has_ligature_sequence(font, (0x1F1FA, 0x1F1F8))
        finally:
            font.close()

    def test_transformed_helper_glyph_metrics_preserved(
        self, output_colrv1_regular, noto_colrv1_font
    ):
        """COLRv1 helper glyph metrics must not collapse to (0, 0).

        Regression test for the browser bug where large transformed emoji such
        as 🟡/🟢 rendered as tiny fragments. The root cause was that merge_emoji_colrv1
        wrote geometry helper glyph hmtx metrics as (0, 0), while Chromium's
        PaintGlyph rendering depends on source-compatible helper metrics.
        """
        out_cmap = output_colrv1_regular["cmap"].getBestCmap() or {}
        src_cmap = noto_colrv1_font["cmap"].getBestCmap() or {}
        out_colr = output_colrv1_regular["COLR"].table
        src_colr = noto_colrv1_font["COLR"].table

        out_records = {r.BaseGlyph: r for r in out_colr.BaseGlyphList.BaseGlyphPaintRecord}
        src_records = {r.BaseGlyph: r for r in src_colr.BaseGlyphList.BaseGlyphPaintRecord}
        out_layers = out_colr.LayerList.Paint
        src_layers = src_colr.LayerList.Paint

        # 🟡 uses the same large-transform helper path as 🟢 and was the clearest
        # regression reproducer in Chromium during manual verification.
        out_glyph = out_cmap[0x1F7E1]
        src_glyph = src_cmap[0x1F7E1]
        out_base = out_records[out_glyph].Paint
        src_base = src_records[src_glyph].Paint

        def _first_transform_helper(layer_list, base_paint):
            for idx in range(base_paint.FirstLayerIndex, base_paint.FirstLayerIndex + base_paint.NumLayers):
                paint = layer_list[idx]
                child = getattr(paint, "Paint", None)
                if getattr(paint, "Format", None) == 12 and child is not None and hasattr(child, "Glyph"):
                    return child.Glyph
            raise AssertionError("Expected a Format=12 PaintTransform layer with helper glyph")

        out_helper = _first_transform_helper(out_layers, out_base)
        src_helper = _first_transform_helper(src_layers, src_base)

        out_metrics = output_colrv1_regular["hmtx"].metrics[out_helper]
        src_adv, src_lsb = noto_colrv1_font["hmtx"].metrics[src_helper]
        upm_scale = (
            output_colrv1_regular["head"].unitsPerEm / noto_colrv1_font["head"].unitsPerEm
        )
        expected = (otRound(src_adv * upm_scale), otRound(src_lsb * upm_scale))

        assert out_metrics != (0, 0), (
            f"Helper glyph {out_helper} metrics collapsed to (0, 0). "
            "This breaks large-transform COLRv1 emoji such as U+1F7E1 🟡 in Chromium."
        )
        assert out_metrics == expected, (
            f"Helper glyph {out_helper} metrics mismatch: expected {expected}, got {out_metrics}"
        )

    def test_all_transformed_helper_glyph_metrics_preserved(
        self, output_colrv1_regular, noto_colrv1_font
    ):
        """All PaintTransform helper glyphs must retain scaled source metrics.

        This broad regression test scans every COLRv1 BaseGlyphPaintRecord in the
        built output. Any helper glyph reached via Format=12 PaintTransform must
        keep the source font's scaled hmtx metrics, rather than collapsing to
        (0, 0). This guards against future regressions beyond the original 🟡/🟢
        reproducer pair.
        """
        out_cmap = output_colrv1_regular["cmap"].getBestCmap() or {}
        src_cmap = noto_colrv1_font["cmap"].getBestCmap() or {}
        out_colr = output_colrv1_regular["COLR"].table
        src_colr = noto_colrv1_font["COLR"].table

        out_records = {r.BaseGlyph: r for r in out_colr.BaseGlyphList.BaseGlyphPaintRecord}
        src_records = {r.BaseGlyph: r for r in src_colr.BaseGlyphList.BaseGlyphPaintRecord}
        out_layers = out_colr.LayerList.Paint
        src_layers = src_colr.LayerList.Paint

        upm_scale = (
            output_colrv1_regular["head"].unitsPerEm / noto_colrv1_font["head"].unitsPerEm
        )

        checked = 0
        failures = []

        def _collect_transform_helpers(paint, layer_list):
            pairs = []

            def walk(node):
                if node is None:
                    return
                fmt = getattr(node, "Format", None)
                if fmt == 12:
                    child = getattr(node, "Paint", None)
                    if child is not None and hasattr(child, "Glyph"):
                        pairs.append(child.Glyph)
                    walk(child)
                    return
                if fmt == 1:
                    for idx in range(node.FirstLayerIndex, node.FirstLayerIndex + node.NumLayers):
                        walk(layer_list[idx])
                    return
                for attr in ("Paint", "SourcePaint", "BackdropPaint"):
                    child = getattr(node, attr, None)
                    if child is not None:
                        walk(child)
                for child in getattr(node, "Paints", []) or []:
                    walk(child)

            walk(paint)
            return pairs

        for cp, out_glyph in out_cmap.items():
            src_glyph = src_cmap.get(cp)
            if src_glyph is None:
                continue
            out_base = out_records.get(out_glyph)
            src_base = src_records.get(src_glyph)
            if out_base is None or src_base is None:
                continue

            out_helpers = _collect_transform_helpers(out_base.Paint, out_layers)
            src_helpers = _collect_transform_helpers(src_base.Paint, src_layers)

            if not out_helpers:
                continue

            checked += len(out_helpers)
            for out_helper, src_helper in zip(out_helpers, src_helpers):
                out_metrics = output_colrv1_regular["hmtx"].metrics[out_helper]
                src_adv, src_lsb = noto_colrv1_font["hmtx"].metrics[src_helper]
                expected = (otRound(src_adv * upm_scale), otRound(src_lsb * upm_scale))
                if out_metrics == (0, 0) or out_metrics != expected:
                    failures.append(
                        f"U+{cp:04X}: helper {out_helper} expected {expected}, got {out_metrics}"
                    )

        assert checked > 50, f"Expected to check many transformed helper glyphs, got {checked}"
        assert not failures, "Transformed helper metric mismatches:\n" + "\n".join(failures[:20])
