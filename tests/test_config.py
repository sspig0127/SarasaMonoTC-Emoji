"""Tests for FontConfig validation (src/config.py)."""

import pytest

from src.config import FontConfig


class TestFontConfigValidation:
    def test_default_is_valid(self):
        """Default FontConfig must construct without error."""
        cfg = FontConfig()
        assert cfg.emoji_width_multiplier == 2

    def test_valid_multiplier_values(self):
        """All values in [1, 4] must be accepted."""
        for v in [1, 2, 3, 4]:
            cfg = FontConfig(emoji_width_multiplier=v)
            assert cfg.emoji_width_multiplier == v

    def test_multiplier_zero_raises(self):
        """emoji_width_multiplier=0 must raise ValueError."""
        with pytest.raises(ValueError, match="between 1 and 4"):
            FontConfig(emoji_width_multiplier=0)

    def test_multiplier_five_raises(self):
        """emoji_width_multiplier=5 must raise ValueError."""
        with pytest.raises(ValueError, match="between 1 and 4"):
            FontConfig(emoji_width_multiplier=5)

    def test_multiplier_negative_raises(self):
        """Negative emoji_width_multiplier must raise ValueError."""
        with pytest.raises(ValueError, match="between 1 and 4"):
            FontConfig(emoji_width_multiplier=-1)

    def test_multiplier_string_raises(self):
        """String emoji_width_multiplier must raise TypeError."""
        with pytest.raises(TypeError, match="must be an int"):
            FontConfig(emoji_width_multiplier="2")

    def test_multiplier_float_raises(self):
        """Float emoji_width_multiplier must raise TypeError."""
        with pytest.raises(TypeError, match="must be an int"):
            FontConfig(emoji_width_multiplier=2.0)

    def test_error_message_contains_value(self):
        """Error message must include the invalid value."""
        with pytest.raises(ValueError) as exc_info:
            FontConfig(emoji_width_multiplier=99)
        assert "99" in str(exc_info.value)
