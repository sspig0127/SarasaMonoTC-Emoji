"""Integration tests for built font output.

These tests verify correctness of the merged fonts produced by build.py.
All tests skip gracefully if the output fonts have not been built yet.

Run after building:
    uv run python build.py --styles Regular
    uv run python build.py --lite --styles Regular
    pytest tests/test_font_output.py -v
"""

import pytest

_KEY_CODEPOINTS = [
    (0x1F600, "😀"),
    (0x1F525, "🔥"),
    (0x4E00, "一"),
]

# Sarasa Mono TC Regular + NotoColorEmoji: well over 56 000 glyphs
_MIN_COLOR_GLYPHS = 56_000
# Sarasa + emoji outlines only: slightly more than Sarasa alone (~3 800 emoji)
_MIN_LITE_GLYPHS = 5_000


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
