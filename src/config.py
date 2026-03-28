"""Font configuration for SarasaMonoTC-Emoji."""

from dataclasses import dataclass

_EMOJI_WIDTH_MIN = 1
_EMOJI_WIDTH_MAX = 4


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

    def __post_init__(self) -> None:
        if not isinstance(self.emoji_width_multiplier, int):
            raise TypeError(
                f"emoji_width_multiplier must be an int, "
                f"got {self.emoji_width_multiplier!r} ({type(self.emoji_width_multiplier).__name__})"
            )
        if not (_EMOJI_WIDTH_MIN <= self.emoji_width_multiplier <= _EMOJI_WIDTH_MAX):
            raise ValueError(
                f"emoji_width_multiplier must be between {_EMOJI_WIDTH_MIN} and {_EMOJI_WIDTH_MAX}, "
                f"got {self.emoji_width_multiplier}"
            )
