#!/usr/bin/env python3
"""
SarasaMonoTC-Emoji Font Builder

Merges NotoColorEmoji (CBDT/CBLC color bitmap) into Sarasa Mono TC,
producing a monospace font with embedded color emoji support.

Background:
  No existing open-source project provides this combination.
  thedemons/merge_color_emoji_font (the only public reference) uses
  FontLab GUI. This is a Python/fonttools automated implementation.

Usage:
    uv run python build.py
    uv run python build.py --styles Regular
    uv run python build.py --styles Regular,Bold --parallel 2
"""

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import yaml

sys.path.insert(0, str(Path(__file__).parent))

from src.config import FontConfig
from src.emoji_merge import merge_emoji, merge_emoji_lite, merge_emoji_colrv1, detect_font_widths, _strip_mac_name_records
from src.utils import update_font_names, verify_glyph_width


def load_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_config_value(yaml_config: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    value = yaml_config
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return default
        if value is None:
            return default
    return value


def get_config_int(
    yaml_config: Dict[str, Any],
    *keys: str,
    default: int,
    min_val: int | None = None,
    max_val: int | None = None,
) -> int:
    """Like get_config_value but validates the result is an integer.

    Raises SystemExit with a friendly message if the value is missing the
    required type or is outside the allowed range — catches config.yaml typos
    before they produce cryptic errors deep in the build pipeline.
    """
    value = get_config_value(yaml_config, *keys, default=default)
    key_path = ".".join(keys)
    if not isinstance(value, int):
        print(
            f"Error: config.yaml '{key_path}' must be an integer, "
            f"got {value!r} ({type(value).__name__})"
        )
        sys.exit(1)
    if min_val is not None and value < min_val:
        print(f"Error: config.yaml '{key_path}' must be >= {min_val}, got {value}")
        sys.exit(1)
    if max_val is not None and value > max_val:
        print(f"Error: config.yaml '{key_path}' must be <= {max_val}, got {value}")
        sys.exit(1)
    return value


def _cleanup_partial_outputs(
    output_dir: Path, family_name_compact: str, styles: list
) -> None:
    """Remove output files for all targeted styles.

    Called after a failed parallel build to avoid leaving a mix of new and
    old font files in the output directory (inconsistent state).
    """
    removed = 0
    for style in styles:
        path = output_dir / f"{family_name_compact}-{style}.ttf"
        if path.exists():
            path.unlink()
            print(f"  Removed: {path.name}")
            removed += 1
    print(f"  Cleaned up {removed} partial output file(s)")


def build_single_font(
    style: str,
    base_font_path: Path,
    emoji_font_path: Path,
    display_name: str,
    output_dir: Path,
    config: FontConfig,
    metadata: dict,
    lite: bool = False,
    colrv1: bool = False,
    max_new_glyphs: int | None = None,
) -> tuple[str, list[dict]]:
    """Build a single font variant with emoji merged in.

    Args:
        style: Font style key (e.g. Regular, Bold)
        base_font_path: Path to SarasaMonoTC-{Style}.ttf
        emoji_font_path: Path to emoji source font
        display_name: Human-readable style name for name table
        output_dir: Output directory
        config: FontConfig object
        metadata: Font metadata dict
        lite: If True, use glyf-based monochrome merge (Lite variant)
        colrv1: If True, use COLRv1 vector merge
        max_new_glyphs: COLRv1 only — glyph budget for greedy selection

    Returns:
        (output_path, selection_records) where selection_records contains
        per-emoji metadata when COLRv1 greedy selection is active, else [].
    """
    style_start = time.monotonic()
    print(f"\nBuilding {config.family_name_compact}-{style}...")

    # Merge emoji into base font
    selection_records: list[dict] = []
    if lite:
        merged_font = merge_emoji_lite(
            base_font_path=str(base_font_path),
            emoji_font_path=str(emoji_font_path),
            config=config,
        )
    elif colrv1:
        merged_font, selection_records = merge_emoji_colrv1(
            base_font_path=str(base_font_path),
            emoji_font_path=str(emoji_font_path),
            config=config,
            max_new_glyphs=max_new_glyphs,
        )
    else:
        merged_font = merge_emoji(
            base_font_path=str(base_font_path),
            emoji_font_path=str(emoji_font_path),
            config=config,
        )

    # Update font metadata
    postscript_name = f"{config.family_name_compact}-{style}"
    print("  Updating font metadata...")
    update_font_names(
        font=merged_font,
        family_name=config.family_name,
        style_name=display_name,
        full_name=f"{config.family_name} {display_name}",
        postscript_name=postscript_name,
        version_str=f"Version {config.version}",
        author=metadata.get("author", ""),
        copyright_str=metadata.get("copyright", ""),
        description=metadata.get("description", ""),
        url=metadata.get("url", ""),
        license_desc=metadata.get("license", ""),
        license_url=metadata.get("license_url", ""),
    )
    # update_font_names() re-introduces Mac platform (platformID=1) name records
    # via set_font_name(..., mac=True). Strip them again so the final font only
    # contains Windows Unicode records (platformID=3), which all modern systems use.
    _strip_mac_name_records(merged_font)

    # Verify glyph widths (detect from font at runtime)
    print("  Verifying glyph widths...")
    from fontTools.ttLib import TTFont as _TTFont
    _base = _TTFont(str(base_font_path))
    half_w, full_w = detect_font_widths(_base)
    _base.close()
    emoji_w = half_w * config.emoji_width_multiplier

    try:
        verify_glyph_width(
            font=merged_font,
            expected_widths=[0, half_w, full_w, emoji_w],
            file_name=postscript_name,
        )
    except ValueError as e:
        print(f"  Warning: {e}")

    # Save
    output_path = output_dir / f"{postscript_name}.ttf"
    merged_font.save(str(output_path))
    merged_font.close()
    elapsed = time.monotonic() - style_start
    print(f"  Saved: {output_path} ({elapsed:.1f}s)")
    return str(output_path), selection_records


def _write_emoji_list(
    records: list[dict],
    output_path: Path,
    version: str,
    max_new_glyphs: int,
) -> None:
    """Write the COLRv1 greedy-selected emoji list as JSON.

    The file is committed to the repository so the selection can be reviewed
    without rebuilding.  All four styles share the same emoji font, so one
    style's selection_records is sufficient.

    Args:
        records: List of per-emoji dicts from _select_colrv1_emoji_greedy.
        output_path: Destination JSON file path (parent dir created if needed).
        version: Font version string for provenance.
        max_new_glyphs: Budget that was used during selection.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_cost = sum(r["new_glyph_cost"] for r in records)
    data = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "max_new_glyphs": max_new_glyphs,
        "selected_count": len(records),
        "total_glyph_cost": total_cost,
        "emoji": records,
    }
    output_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nEmoji list written: {output_path} ({len(records)} emoji, cost: {total_cost})")


def main():
    default_config_path = Path(__file__).parent / "config.yaml"

    parser = argparse.ArgumentParser(
        description="Build SarasaMonoTC-Emoji font",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run python build.py
  uv run python build.py --styles Regular
  uv run python build.py --styles Regular,Bold --parallel 2

Configuration priority: CLI args > config.yaml > defaults
        """,
    )
    parser.add_argument("--config", type=Path, default=default_config_path)
    parser.add_argument("--styles", type=str, default=None,
                        help="Comma-separated styles to build")
    parser.add_argument("--fonts-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--parallel", type=int, default=None)
    parser.add_argument("--lite", action="store_true",
                        help="Build Lite variant: monochrome glyf emoji (VHS-compatible, smaller files). "
                             "Requires NotoEmoji[wght].ttf in fonts/ directory.")
    parser.add_argument("--colrv1", action="store_true",
                        help="Build COLRv1 variant: color vector emoji (Chrome 98+, smaller than CBDT). "
                             "Requires Noto-COLRv1.ttf in fonts/ directory.")

    args = parser.parse_args()

    if args.lite and args.colrv1:
        print("Error: --lite and --colrv1 are mutually exclusive")
        sys.exit(1)

    yaml_config = load_config(args.config)

    styles_config = get_config_value(yaml_config, "styles") or {}
    if not styles_config:
        print("Error: No styles defined in config.yaml")
        sys.exit(1)

    styles_str = (
        args.styles
        or get_config_value(yaml_config, "build", "styles")
        or ",".join(styles_config.keys())
    )
    fonts_dir = args.fonts_dir or Path(get_config_value(yaml_config, "fonts_dir") or "fonts")
    parallel = (
        args.parallel
        if args.parallel is not None
        else get_config_int(yaml_config, "build", "parallel", default=1, min_val=1)
    )

    is_lite = args.lite
    is_colrv1 = args.colrv1

    # Determine family name, output dir, and emoji font override based on variant
    if is_colrv1:
        family_name = (
            get_config_value(yaml_config, "colrv1", "family_name")
            or (get_config_value(yaml_config, "font", "family_name") or "SarasaMonoTCEmoji") + "COLRv1"
        )
        variant_emoji_font = get_config_value(yaml_config, "colrv1", "emoji_font") or "Noto-COLRv1.ttf"
        default_output_dir = get_config_value(yaml_config, "colrv1", "output_dir") or "output/fonts-colrv1"
        colrv1_max_new_glyphs: int | None = get_config_int(
            yaml_config, "colrv1", "max_new_glyphs", default=8136
        )
        colrv1_emoji_list_path = Path(
            get_config_value(yaml_config, "colrv1", "emoji_list_path")
            or "docs/colrv1-emoji-list.json"
        )
    elif is_lite:
        family_name = (
            get_config_value(yaml_config, "lite", "family_name")
            or (get_config_value(yaml_config, "font", "family_name") or "SarasaMonoTCEmoji") + "Lite"
        )
        variant_emoji_font = get_config_value(yaml_config, "lite", "emoji_font") or "NotoEmoji[wght].ttf"
        default_output_dir = get_config_value(yaml_config, "lite", "output_dir") or "output/fonts-lite"
        colrv1_max_new_glyphs = None
        colrv1_emoji_list_path = None
    else:
        family_name = get_config_value(yaml_config, "font", "family_name") or "SarasaMonoTCEmoji"
        variant_emoji_font = None
        default_output_dir = get_config_value(yaml_config, "build", "output_dir") or "output/fonts"
        colrv1_max_new_glyphs = None
        colrv1_emoji_list_path = None

    output_dir = args.output_dir or Path(default_output_dir)

    version = get_config_value(yaml_config, "font", "version") or "1.0"

    metadata = {
        "author": get_config_value(yaml_config, "font", "author") or "",
        "copyright": get_config_value(yaml_config, "font", "copyright") or "",
        "description": (
            get_config_value(yaml_config, "colrv1", "description")
            if is_colrv1
            else get_config_value(yaml_config, "lite", "description")
            if is_lite
            else get_config_value(yaml_config, "font", "description")
        ) or "",
        "url": get_config_value(yaml_config, "font", "url") or "",
        "license": get_config_value(yaml_config, "font", "license") or "",
        "license_url": get_config_value(yaml_config, "font", "license_url") or "",
    }

    config = FontConfig(
        family_name=family_name,
        family_name_compact=family_name,
        version=version,
        emoji_width_multiplier=get_config_int(
            yaml_config, "emoji", "emoji_width_multiplier", default=2, min_val=1, max_val=4
        ),
        skip_existing=get_config_value(
            yaml_config, "emoji", "skip_existing", default=True
        ),
    )

    styles = [s.strip() for s in styles_str.split(",")]
    valid_styles = list(styles_config.keys())
    for style in styles:
        if style not in valid_styles:
            print(f"Error: Invalid style '{style}'. Valid: {valid_styles}")
            sys.exit(1)

    # Validate font paths
    font_paths: Dict[str, Dict[str, Any]] = {}
    for style in styles:
        style_cfg = styles_config[style]
        base_font = style_cfg.get("base_font")
        # Variant-specific emoji font override (COLRv1 or Lite replace per-style emoji font)
        emoji_font = variant_emoji_font or style_cfg.get("emoji_font")
        display_name = style_cfg.get("display_name", style)

        if not base_font or not emoji_font:
            print(f"Error: Style '{style}' must have both 'base_font' and 'emoji_font'")
            sys.exit(1)

        base_path = fonts_dir / base_font
        emoji_path = fonts_dir / emoji_font

        if not base_path.exists():
            print(f"Error: Base font not found: {base_path}")
            print(f"  Download from: https://github.com/be5invis/Sarasa-Gothic/releases")
            sys.exit(1)
        if not emoji_path.exists():
            print(f"Error: Emoji font not found: {emoji_path}")
            if is_colrv1:
                print(f"  Download Noto-COLRv1.ttf (COLRv1 color vector font) from:")
                print(f"    https://github.com/googlefonts/noto-emoji/blob/main/fonts/Noto-COLRv1.ttf")
                print(f"  Place it at: {emoji_path}")
            elif is_lite:
                print(f"  Download NotoEmoji[wght].ttf (monochrome variable font) from:")
                print(f"    https://github.com/google/fonts/raw/main/ofl/notoemoji/NotoEmoji%5Bwght%5D.ttf")
                print(f"  Place it at: {emoji_path}")
            else:
                print(f"  Download from: https://github.com/googlefonts/noto-emoji/releases")
            sys.exit(1)

        font_paths[style] = {
            "base_font_path": base_path,
            "emoji_font_path": emoji_path,
            "display_name": display_name,
        }

    output_dir.mkdir(parents=True, exist_ok=True)

    variant_label = (
        "COLRv1 (color vector)" if is_colrv1
        else "Lite (monochrome glyf)" if is_lite
        else "Color (CBDT/CBLC)"
    )
    print(f"Building {config.family_name} v{config.version} [{variant_label}]")
    print(f"Styles: {', '.join(styles)}")
    print(f"Source: {fonts_dir}")
    print(f"Output: {output_dir}")
    print(f"Emoji width: {config.emoji_width_multiplier}x half-width")
    if is_colrv1 and colrv1_max_new_glyphs is not None:
        print(f"Glyph budget: {colrv1_max_new_glyphs} new slots (greedy selection)")
    print("Font mapping:")
    for style in styles:
        p = font_paths[style]
        print(f"  {style}: {p['base_font_path'].name} + {p['emoji_font_path'].name}")

    build_start = time.monotonic()
    colrv1_selection_records: list[dict] = []

    if parallel <= 1:
        for style in styles:
            p = font_paths[style]
            _, records = build_single_font(
                style, p["base_font_path"], p["emoji_font_path"],
                p["display_name"], output_dir, config, metadata,
                lite=is_lite, colrv1=is_colrv1,
                max_new_glyphs=colrv1_max_new_glyphs,
            )
            if records and not colrv1_selection_records:
                colrv1_selection_records = records
    else:
        try:
            with ProcessPoolExecutor(max_workers=parallel) as executor:
                futures = {}
                for style in styles:
                    p = font_paths[style]
                    future = executor.submit(
                        build_single_font,
                        style, p["base_font_path"], p["emoji_font_path"],
                        p["display_name"], output_dir, config, metadata,
                        is_lite, is_colrv1,
                        colrv1_max_new_glyphs,
                    )
                    futures[future] = style

                for future in as_completed(futures):
                    style = futures[future]
                    try:
                        _, records = future.result()
                        if records and not colrv1_selection_records:
                            colrv1_selection_records = records
                    except Exception as e:
                        print(f"\nError building {style}: {e}")
                        for f in futures:
                            f.cancel()
                        raise
        except Exception:
            print("\nParallel build failed — cleaning up partial outputs...")
            _cleanup_partial_outputs(output_dir, config.family_name_compact, styles)
            raise

    build_elapsed = time.monotonic() - build_start

    # Write COLRv1 emoji selection list (committed to repo for reference)
    if is_colrv1 and colrv1_selection_records and colrv1_emoji_list_path is not None:
        _write_emoji_list(
            records=colrv1_selection_records,
            output_path=colrv1_emoji_list_path,
            version=version,
            max_new_glyphs=colrv1_max_new_glyphs,
        )

    # Generate manifest for verify-emoji.html
    manifest = {
        "family_name": config.family_name,
        "version": config.version,
        "fonts": [],
    }
    for style in styles:
        manifest["fonts"].append({
            "style": style,
            "display_name": font_paths[style]["display_name"],
            "filename": f"{config.family_name_compact}-{style}.ttf",
        })

    manifest_path = output_dir / "fonts-manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"\nGenerated manifest: {manifest_path}")
    print(f"Build complete! Fonts saved to: {output_dir} (total: {build_elapsed:.1f}s)")


if __name__ == "__main__":
    main()
