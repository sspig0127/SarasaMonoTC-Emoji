"""Font configuration for SarasaMonoTC-Emoji."""

from dataclasses import dataclass


@dataclass
class FontConfig:
    """Configuration for font building."""

    # Font naming
    family_name: str = "SarasaMonoTCEmoji"
    family_name_compact: str = "SarasaMonoTCEmoji"
    version: str = "1.0"

    # Emoji width: how many half-widths an emoji occupies
    # 2 = full-width (same as CJK), required for proper monospace alignment
    emoji_width_multiplier: int = 2

    # Whether to skip codepoints already present in base font
    # Prevents overwriting Sarasa's existing symbol glyphs
    skip_existing: bool = True
