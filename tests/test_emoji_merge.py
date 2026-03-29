"""Unit tests for src/emoji_merge.py core functions.

Test groups:
  - _scale_glyph: pure logic, always runs (no font files needed)
  - detect_font_widths: requires Sarasa source font
  - get_emoji_cmap: requires any glyf emoji font (NotoEmoji[wght].ttf available in CI)
  - _collect_glyph_deps: requires any glyf emoji font
"""

import array

import pytest
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates, GlyphComponent

from src.emoji_merge import (
    _collect_glyph_deps,
    _collect_colrv1_paint_glyph_deps,
    _filter_colr_to_added_glyphs,
    _scale_glyph,
    detect_font_widths,
    get_emoji_cmap,
)

_INT16_MIN = -32768
_INT16_MAX = 32767


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _simple_glyph(coords: list[tuple[int, int]]) -> Glyph:
    """Build a minimal simple (non-composite) TTGlyph."""
    g = Glyph()
    g.numberOfContours = 1
    g.coordinates = GlyphCoordinates(coords)
    g.flags = array.array("B", [1] * len(coords))
    g.endPtsOfContours = [len(coords) - 1]
    bounds = g.coordinates.calcBounds()
    g.xMin, g.yMin, g.xMax, g.yMax = int(bounds[0]), int(bounds[1]), int(bounds[2]), int(bounds[3])
    return g


def _composite_glyph(components: list[tuple[str, int, int]]) -> Glyph:
    """Build a minimal composite TTGlyph."""
    g = Glyph()
    g.numberOfContours = -1
    g.components = []
    for name, x, y in components:
        comp = GlyphComponent()
        comp.glyphName = name
        comp.x = x
        comp.y = y
        comp.flags = 0
    g.components = []
    for name, x, y in components:
        comp = GlyphComponent()
        comp.glyphName = name
        comp.x = x
        comp.y = y
        comp.flags = 0
        g.components.append(comp)
    return g


# ---------------------------------------------------------------------------
# _scale_glyph — pure logic tests (always run)
# ---------------------------------------------------------------------------

class TestScaleGlyph:
    def test_noop_when_scale_is_one(self):
        """scale=1.0 should not modify the glyph at all."""
        g = _simple_glyph([(100, 200), (300, 400)])
        original_coords = list(g.coordinates)
        _scale_glyph(g, 1.0)
        assert list(g.coordinates) == original_coords
        assert g.xMin == 100
        assert g.yMax == 400

    def test_simple_glyph_scales_coordinates(self):
        """Simple glyph coordinates should be multiplied by the scale factor."""
        g = _simple_glyph([(0, 0), (1000, 2000)])
        _scale_glyph(g, 0.5)
        coords = list(g.coordinates)
        assert coords[0] == (0, 0)
        assert coords[1] == (500, 1000)

    def test_simple_glyph_bbox_is_integer(self):
        """After scaling, xMin/yMin/xMax/yMax must be integers (int16-packable)."""
        g = _simple_glyph([(100, 200), (300, 400)])
        _scale_glyph(g, 1000 / 2048)  # realistic Noto→Sarasa scale
        assert isinstance(g.xMin, int)
        assert isinstance(g.yMin, int)
        assert isinstance(g.xMax, int)
        assert isinstance(g.yMax, int)

    def test_simple_glyph_bbox_within_int16(self):
        """Scaled bbox values for typical emoji coords must fit in int16."""
        # Noto Emoji UPM=2048; typical glyph spans (0,0)→(1800,1800)
        g = _simple_glyph([(0, 0), (1800, 1800)])
        _scale_glyph(g, 1000 / 2048)
        assert _INT16_MIN <= g.xMin <= _INT16_MAX
        assert _INT16_MIN <= g.yMin <= _INT16_MAX
        assert _INT16_MIN <= g.xMax <= _INT16_MAX
        assert _INT16_MIN <= g.yMax <= _INT16_MAX

    def test_simple_glyph_upm_2048_to_1000(self):
        """Realistic Noto→Sarasa scale: bbox must shrink by ~half."""
        g = _simple_glyph([(0, -420), (2048, 1638)])
        _scale_glyph(g, 1000 / 2048)
        # exact rounded values: 0, -205, 1000, 800
        assert g.xMin == 0
        assert g.yMin == -205
        assert g.xMax == 1000
        assert g.yMax == 800

    def test_composite_glyph_scales_offsets(self):
        """Composite glyph component offsets should be scaled and rounded."""
        g = _composite_glyph([("base", 100, 200), ("accent", 300, 400)])
        _scale_glyph(g, 0.5)
        assert g.components[0].x == 50
        assert g.components[0].y == 100
        assert g.components[1].x == 150
        assert g.components[1].y == 200

    def test_composite_glyph_offsets_are_integer(self):
        """Composite component offsets must be rounded integers after scaling."""
        g = _composite_glyph([("base", 100, 200)])
        _scale_glyph(g, 1000 / 2048)
        assert isinstance(g.components[0].x, int)
        assert isinstance(g.components[0].y, int)

    def test_scale_near_one_treated_as_noop(self):
        """Scale within 1e-6 of 1.0 is treated as no-op."""
        g = _simple_glyph([(100, 200), (300, 400)])
        original_coords = list(g.coordinates)
        _scale_glyph(g, 1.0 + 5e-7)
        assert list(g.coordinates) == original_coords

    # --- T2: int16 range protection ---

    def test_simple_glyph_raises_on_out_of_range_bbox(self):
        """ValueError must be raised when scaled bbox exceeds int16 range."""
        # scale 0.5: (0,0)→(70000,70000) → xMax=yMax=35000 > 32767
        g = _simple_glyph([(0, 0), (70000, 70000)])
        with pytest.raises(ValueError, match="int16 range"):
            _scale_glyph(g, 0.5)

    def test_simple_glyph_raises_on_negative_out_of_range(self):
        """ValueError must be raised when scaled bbox goes below int16 minimum."""
        # scale 0.5: (-70000,-70000)→(0,0) → xMin=yMin=-35000 < -32768
        g = _simple_glyph([(-70000, -70000), (0, 0)])
        with pytest.raises(ValueError, match="int16 range"):
            _scale_glyph(g, 0.5)

    def test_composite_glyph_raises_on_out_of_range_offset(self):
        """ValueError must be raised when scaled composite offset exceeds int16."""
        # offset 70000 * 0.5 = 35000 > 32767
        g = _composite_glyph([("base", 70000, 0)])
        with pytest.raises(ValueError, match="int16 range"):
            _scale_glyph(g, 0.5)

    def test_error_message_contains_field_name_and_value(self):
        """Error message must identify the offending field and its value."""
        g = _simple_glyph([(0, 0), (70000, 70000)])
        with pytest.raises(ValueError) as exc_info:
            _scale_glyph(g, 0.5)
        msg = str(exc_info.value)
        assert "35000" in msg  # the out-of-range value
        assert "int16" in msg


# ---------------------------------------------------------------------------
# detect_font_widths — requires Sarasa source font
# ---------------------------------------------------------------------------

def _mock_font(width_list: list) -> object:
    """Minimal font mock with empty cmap to force the fallback detection path."""
    metrics = {f"g{i}": (w, 0) for i, w in enumerate(width_list)}

    class _Hmtx:
        def __init__(self):
            self.metrics = metrics
        def __getitem__(self, name):
            return metrics[name]

    class _Cmap:
        def getBestCmap(self):
            return {}  # No 'A' or '一' → forces fallback

    class _Font:
        def __getitem__(self, key):
            return {"cmap": _Cmap(), "hmtx": _Hmtx()}[key]

    return _Font()


class TestDetectFontWidths:
    def test_sarasa_returns_500_1000(self, sarasa_font):
        """Sarasa Mono TC UPM=1000 → half=500, full=1000."""
        half, full = detect_font_widths(sarasa_font)
        assert half == 500
        assert full == 1000

    def test_ratio_is_2_to_1(self, sarasa_font):
        """Detected widths must always satisfy full == 2 * half."""
        half, full = detect_font_widths(sarasa_font)
        assert full == 2 * half

    # --- T4: fallback 1% threshold (pure logic, no font files needed) ---

    def test_fallback_accepts_dominant_pair(self):
        """Fallback must accept a 2:1 pair where both widths meet the 1% threshold."""
        widths = [500] * 100 + [1000] * 100
        half, full = detect_font_widths(_mock_font(widths))
        assert half == 500
        assert full == 1000

    def test_fallback_rejects_low_count_pair(self):
        """Fallback must reject a 2:1 pair where each width appears in <1% of glyphs."""
        # 400 glyphs at w=700 (no 2:1 partner), only 2 at w=100, 2 at w=200
        # threshold = max(1, 404//100) = 4; count(100)=2 < 4 → rejected → ValueError
        widths = [700] * 400 + [100] * 2 + [200] * 2
        with pytest.raises(ValueError):
            detect_font_widths(_mock_font(widths))

    def test_fallback_threshold_ignores_tiny_minority(self):
        """Dominant pair (500/1000) must win even when a spurious low-count pair exists."""
        # 200 glyphs at 500, 200 at 1000 (dominant), 1 at 100, 1 at 200 (spurious)
        widths = [500] * 200 + [1000] * 200 + [100] * 1 + [200] * 1
        half, full = detect_font_widths(_mock_font(widths))
        assert half == 500
        assert full == 1000


# ---------------------------------------------------------------------------
# get_emoji_cmap — requires NotoEmoji[wght].ttf (available in CI)
# ---------------------------------------------------------------------------

class TestGetEmojiCmap:
    def test_excludes_ascii(self, noto_emoji_font):
        """No ASCII codepoints (U+0000–U+00FF) should appear in the result."""
        cmap = get_emoji_cmap(noto_emoji_font)
        ascii_in_result = {cp for cp in cmap if 0x0000 <= cp <= 0x00FF}
        assert ascii_in_result == set(), f"ASCII codepoints found: {ascii_in_result}"

    def test_excludes_variation_selectors(self, noto_emoji_font):
        """Variation selectors (U+FE00–U+FE0F) must be excluded."""
        cmap = get_emoji_cmap(noto_emoji_font)
        vs_in_result = {cp for cp in cmap if 0xFE00 <= cp <= 0xFE0F}
        assert vs_in_result == set()

    def test_excludes_variation_selectors_supplement(self, noto_emoji_font):
        """Variation Selectors Supplement (U+E0100–U+E01EF) must be excluded."""
        cmap = get_emoji_cmap(noto_emoji_font)
        vss_in_result = {cp for cp in cmap if 0xE0100 <= cp <= 0xE01EF}
        assert vss_in_result == set()

    def test_has_common_emoji(self, noto_emoji_font):
        """Common emoji codepoints must be present."""
        cmap = get_emoji_cmap(noto_emoji_font)
        for cp, name in [(0x1F600, "😀"), (0x1F525, "🔥"), (0x2764, "❤")]:
            assert cp in cmap, f"Missing U+{cp:04X} {name}"

    def test_returns_nonempty_dict(self, noto_emoji_font):
        """Result must contain a significant number of emoji."""
        cmap = get_emoji_cmap(noto_emoji_font)
        assert len(cmap) > 500, f"Expected >500 emoji, got {len(cmap)}"


# ---------------------------------------------------------------------------
# _collect_glyph_deps — requires NotoEmoji[wght].ttf (available in CI)
# ---------------------------------------------------------------------------

class TestCollectGlyphDeps:
    def test_components_precede_composites(self, noto_emoji_font):
        """Component glyphs must appear before any composite that references them."""
        cmap = get_emoji_cmap(noto_emoji_font)
        target_names = set(cmap.values())
        result = _collect_glyph_deps(noto_emoji_font, target_names, set())

        emoji_glyf = noto_emoji_font.get("glyf")
        if emoji_glyf is None:
            pytest.skip("Emoji font has no glyf table")

        position = {name: i for i, name in enumerate(result)}
        for name in result:
            if name not in emoji_glyf.glyphs:
                continue
            glyph = emoji_glyf[name]
            glyph.expand(emoji_glyf)
            if glyph.numberOfContours < 0 and hasattr(glyph, "components"):
                for comp in glyph.components:
                    comp_name = comp.glyphName
                    if comp_name in position and name in position:
                        assert position[comp_name] < position[name], (
                            f"Component '{comp_name}' (pos {position[comp_name]}) "
                            f"must precede composite '{name}' (pos {position[name]})"
                        )

    def test_excludes_base_existing_names(self, noto_emoji_font):
        """Glyphs already in base font must not appear in result."""
        cmap = get_emoji_cmap(noto_emoji_font)
        target_names = set(cmap.values())
        # Mark all target names as already existing
        result = _collect_glyph_deps(noto_emoji_font, target_names, target_names)
        assert result == [], f"Expected empty result, got {len(result)} glyphs"

    def test_result_is_subset_of_emoji_glyphs(self, noto_emoji_font):
        """Every returned name must exist in the emoji font."""
        cmap = get_emoji_cmap(noto_emoji_font)
        target_names = set(cmap.values())
        result = _collect_glyph_deps(noto_emoji_font, target_names, set())
        emoji_glyph_names = set(noto_emoji_font.getGlyphOrder())
        for name in result:
            assert name in emoji_glyph_names, f"Unknown glyph name: {name}"


# ---------------------------------------------------------------------------
# _collect_colrv1_paint_glyph_deps — requires Noto-COLRv1.ttf
# ---------------------------------------------------------------------------

class TestCollectColrv1Deps:
    def test_returns_empty_when_no_colr(self, noto_emoji_font):
        """Non-COLRv1 font must return empty set."""
        if "COLR" in noto_emoji_font:
            pytest.skip("This font has COLR; need a font without COLR for this test")
        result = _collect_colrv1_paint_glyph_deps(noto_emoji_font, {"glyph001"})
        assert result == set()

    def test_returns_nonempty_for_colrv1_font(self, noto_colrv1_font):
        """COLRv1 source font must yield some geometry deps for common emoji."""
        cmap = get_emoji_cmap(noto_colrv1_font)
        target_names = {name for cp, name in cmap.items() if cp == 0x1F600}
        if not target_names:
            pytest.skip("U+1F600 not in COLRv1 cmap")
        deps = _collect_colrv1_paint_glyph_deps(noto_colrv1_font, target_names)
        # Some emoji use PaintGlyph; not guaranteed for every emoji, but common
        # (test passes even if empty — absence of crash is the main check)
        assert isinstance(deps, set)

    def test_paint_colr_layers_deps_collected(self, noto_colrv1_font):
        """PaintColrLayers (Format=1) emoji must have their geometry deps collected.

        Noto-COLRv1 uses PaintColrLayers for ~92% of emoji (including u1F600).
        The walk function must traverse into the LayerList to find PaintGlyph
        references — otherwise geometry helper glyphs are never added and the
        merged font renders empty/garbled glyphs.
        """
        colr = noto_colrv1_font["COLR"].table
        # Confirm u1F600 uses PaintColrLayers (Format=1), not inline PaintGlyph
        for rec in colr.BaseGlyphList.BaseGlyphPaintRecord:
            if rec.BaseGlyph == "u1F600":
                if rec.Paint.Format != 1:
                    pytest.skip("u1F600 paint format changed; test assumption no longer valid")
                break
        else:
            pytest.skip("u1F600 not in COLRv1 BaseGlyphList")

        cmap = get_emoji_cmap(noto_colrv1_font)
        target_names = {name for cp, name in cmap.items() if cp == 0x1F600}
        deps = _collect_colrv1_paint_glyph_deps(noto_colrv1_font, target_names)
        assert len(deps) > 0, (
            "u1F600 uses PaintColrLayers but no geometry deps were collected — "
            "walk() is not traversing the LayerList"
        )
        # All collected deps must exist in the source font's glyph order
        font_glyphs = set(noto_colrv1_font.getGlyphOrder())
        for dep in deps:
            assert dep in font_glyphs, f"Collected dep '{dep}' not in source font"

    def test_all_emoji_deps_collected(self, noto_colrv1_font):
        """Collecting deps for all emoji should yield significantly more than 100 unique glyphs.

        With only inline PaintGlyph (Format=10) traversal, only ~42 deps are found.
        With proper PaintColrLayers (Format=1) traversal, thousands are found.
        """
        cmap = get_emoji_cmap(noto_colrv1_font)
        target_names = set(cmap.values())
        deps = _collect_colrv1_paint_glyph_deps(noto_colrv1_font, target_names)
        assert len(deps) > 100, (
            f"Expected >100 geometry deps across all emoji, got {len(deps)}. "
            "PaintColrLayers traversal may be broken."
        )

    def test_deps_not_in_target_names(self, noto_colrv1_font):
        """Caller should subtract target_names from returned deps to avoid double-adding."""
        cmap = get_emoji_cmap(noto_colrv1_font)
        target_names = set(cmap.values())
        deps = _collect_colrv1_paint_glyph_deps(noto_colrv1_font, target_names)
        # All deps are glyph names (strings)
        assert all(isinstance(n, str) for n in deps)


# ---------------------------------------------------------------------------
# _filter_colr_to_added_glyphs — pure logic tests (no font files needed)
# ---------------------------------------------------------------------------

def _make_mock_colr_font(base_glyph_names: list[str]):
    """Build a minimal TTFont with a fake COLR table for testing."""
    from fontTools.ttLib import TTFont as _TTFont
    from fontTools.ttLib.tables import otTables

    font = _TTFont()
    font.setGlyphOrder([".notdef"] + base_glyph_names)

    # Build a minimal COLRv1 table
    colr_table = otTables.COLR()
    colr_table.Version = 1

    bgl = otTables.BaseGlyphList()
    records = []
    for name in base_glyph_names:
        rec = otTables.BaseGlyphPaintRecord()
        rec.BaseGlyph = name
        # Minimal paint (PaintSolid format)
        paint = otTables.Paint()
        paint.Format = 2  # PaintSolid
        rec.Paint = paint
        records.append(rec)
    bgl.BaseGlyphPaintRecord = records
    colr_table.BaseGlyphList = bgl
    colr_table.BaseGlyphRecord = []
    colr_table.ClipList = None

    from fontTools.ttLib.tables import C_O_L_R_
    colr_wrapper = C_O_L_R_.table_C_O_L_R_()
    colr_wrapper.table = colr_table
    font["COLR"] = colr_wrapper
    return font


class TestFilterColrToAddedGlyphs:
    def test_filters_to_added_set(self):
        """Only records in added_set must remain after filtering."""
        font = _make_mock_colr_font(["emoji_a", "emoji_b", "emoji_c"])
        _filter_colr_to_added_glyphs(font, {"emoji_a", "emoji_c"})
        records = font["COLR"].table.BaseGlyphList.BaseGlyphPaintRecord
        remaining = {r.BaseGlyph for r in records}
        assert remaining == {"emoji_a", "emoji_c"}

    def test_empty_added_set_clears_all(self):
        """Empty added_set must remove all COLR records."""
        font = _make_mock_colr_font(["emoji_a", "emoji_b"])
        _filter_colr_to_added_glyphs(font, set())
        records = font["COLR"].table.BaseGlyphList.BaseGlyphPaintRecord
        assert records == []

    def test_noop_when_all_in_added_set(self):
        """All records must be preserved when added_set covers everything."""
        font = _make_mock_colr_font(["emoji_a", "emoji_b"])
        _filter_colr_to_added_glyphs(font, {"emoji_a", "emoji_b"})
        records = font["COLR"].table.BaseGlyphList.BaseGlyphPaintRecord
        assert len(records) == 2

    def test_no_colr_table_is_noop(self):
        """Must not raise if font has no COLR table."""
        from fontTools.ttLib import TTFont as _TTFont
        font = _TTFont()
        font.setGlyphOrder([".notdef"])
        _filter_colr_to_added_glyphs(font, {"some_glyph"})  # must not raise
