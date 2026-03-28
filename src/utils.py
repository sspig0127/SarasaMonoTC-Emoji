"""Utility functions for font manipulation.

Adapted from JetBrainsLxgwNerdMono/src/utils.py
Changes: vendor_id in unique_id changed from JBLXGW to SMTCE.
"""

from typing import List, Optional, Tuple

from fontTools.ttLib import TTFont


def set_font_name(
    font: TTFont,
    name: str,
    name_id: int,
    mac: bool = False,
    lang_id: int = 0x409,
) -> None:
    """Set font name entry.

    Args:
        font: TTFont object
        name: Name string to set
        name_id: Name table ID
        mac: Whether to also set Mac platform entry
        lang_id: Language ID (default 0x409 for US English)
    """
    name_table = font["name"]

    if lang_id == 0x409:
        name_table.removeNames(nameID=name_id)

    name_table.setName(
        name, nameID=name_id, platformID=3, platEncID=1, langID=lang_id
    )

    if mac and lang_id == 0x409:
        name_table.setName(
            name, nameID=name_id, platformID=1, platEncID=0, langID=0x0
        )


def update_font_names(
    font: TTFont,
    family_name: str,
    style_name: str,
    full_name: str,
    postscript_name: str,
    version_str: str,
    author: str = "",
    copyright_str: str = "",
    description: str = "",
    url: str = "",
    license_desc: str = "",
    license_url: str = "",
) -> None:
    """Update font metadata names.

    Args:
        font: TTFont object
        family_name: Font family name (NameID 1)
        style_name: Font subfamily/style name (NameID 2)
        full_name: Full font name (NameID 4)
        postscript_name: PostScript name (NameID 6)
        version_str: Version string (NameID 5)
        author: Author/designer name (NameID 8, 9)
        copyright_str: Copyright notice (NameID 0)
        description: Font description (NameID 10)
        url: Vendor/Designer URL (NameID 11, 12)
        license_desc: License description (NameID 13)
        license_url: License URL (NameID 14)
    """
    unique_id = f"{version_str};SMTCE;{postscript_name}"

    if copyright_str:
        set_font_name(font, copyright_str, 0)
    set_font_name(font, family_name, 1, mac=True)
    set_font_name(font, style_name, 2, mac=True)
    set_font_name(font, unique_id, 3)
    set_font_name(font, full_name, 4, mac=True)
    set_font_name(font, version_str, 5)
    set_font_name(font, postscript_name, 6, mac=True)
    font["name"].removeNames(nameID=7)
    if author:
        set_font_name(font, author, 8)
    if author:
        set_font_name(font, author, 9)
    if description:
        set_font_name(font, description, 10)
    if url:
        set_font_name(font, url, 11)
    if url:
        set_font_name(font, url, 12)
    if license_desc:
        set_font_name(font, license_desc, 13)
    if license_url:
        set_font_name(font, license_url, 14)

    set_font_name(font, family_name, 16)
    set_font_name(font, style_name, 17)

    # Add Traditional Chinese names for better CJK app compatibility
    tc_lang_id = 0x404
    set_font_name(font, family_name, 1, mac=False, lang_id=tc_lang_id)
    set_font_name(font, style_name, 2, mac=False, lang_id=tc_lang_id)
    set_font_name(font, full_name, 4, mac=False, lang_id=tc_lang_id)
    set_font_name(font, family_name, 16, mac=False, lang_id=tc_lang_id)
    set_font_name(font, style_name, 17, mac=False, lang_id=tc_lang_id)


def merge_os2_ranges(target_font: TTFont, source_font: TTFont) -> None:
    """Merge OS/2 table Unicode ranges and Code Page ranges.

    Args:
        target_font: The font to update
        source_font: The source font (emoji font)
    """
    if "OS/2" not in target_font or "OS/2" not in source_font:
        return

    target_os2 = target_font["OS/2"]
    source_os2 = source_font["OS/2"]

    if hasattr(target_os2, "ulUnicodeRange1") and hasattr(source_os2, "ulUnicodeRange1"):
        target_os2.ulUnicodeRange1 |= source_os2.ulUnicodeRange1
        target_os2.ulUnicodeRange2 |= source_os2.ulUnicodeRange2
        target_os2.ulUnicodeRange3 |= source_os2.ulUnicodeRange3
        target_os2.ulUnicodeRange4 |= source_os2.ulUnicodeRange4
        print("  Merged OS/2 Unicode Ranges")

    if hasattr(target_os2, "ulCodePageRange1") and hasattr(source_os2, "ulCodePageRange1"):
        target_os2.ulCodePageRange1 |= source_os2.ulCodePageRange1
        target_os2.ulCodePageRange2 |= source_os2.ulCodePageRange2
        print("  Merged OS/2 Code Page Ranges")


def verify_glyph_width(
    font: TTFont, expected_widths: List[int], file_name: Optional[str] = None
) -> None:
    """Verify all glyph widths are within expected values.

    Args:
        font: TTFont object
        expected_widths: List of valid advance widths
        file_name: Optional file name for error messages
    """
    unexpected = []
    hmtx = font["hmtx"]

    for name in font.getGlyphOrder():
        width, _ = hmtx[name]
        if width not in expected_widths and width != 0:
            unexpected.append((name, width))

    if not unexpected:
        print(f"  Verified glyph widths in {file_name or 'font'}")
        return

    sample = unexpected[:10]
    sample_str = "\n".join(f"  {name}: {width}" for name, width in sample)
    raise ValueError(
        f"Found {len(unexpected)} glyphs with unexpected widths "
        f"(expected {expected_widths}):\n{sample_str}"
    )
