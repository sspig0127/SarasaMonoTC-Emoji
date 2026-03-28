"""Shared fixtures for SarasaMonoTC-Emoji tests.

Font availability determines which tests run:
  - Pure logic tests: always run (no font files needed)
  - Source font tests: skip if fonts/ directory is absent
  - Output tests: skip if output/ has not been built

All fixtures use session scope to avoid reopening large font files repeatedly.
"""

import sys
from pathlib import Path

import pytest

# Make project root importable so `from src.xxx import ...` works when pytest
# is run from the project root (the normal case) or from the tests/ subdirectory.
_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

FONTS_DIR = _ROOT / "fonts"
OUTPUT_COLOR_DIR = _ROOT / "output" / "fonts"
OUTPUT_LITE_DIR = _ROOT / "output" / "fonts-lite"

_SARASA_REGULAR = FONTS_DIR / "SarasaMonoTC-Regular.ttf"
_NOTO_COLOR_EMOJI = FONTS_DIR / "NotoColorEmoji.ttf"
_NOTO_EMOJI = FONTS_DIR / "NotoEmoji[wght].ttf"
_OUTPUT_COLOR_REGULAR = OUTPUT_COLOR_DIR / "SarasaMonoTCEmoji-Regular.ttf"
_OUTPUT_LITE_REGULAR = OUTPUT_LITE_DIR / "SarasaMonoTCEmojiLite-Regular.ttf"


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_sarasa: test requires Sarasa source font")
    config.addinivalue_line("markers", "requires_noto_color: test requires NotoColorEmoji.ttf")
    config.addinivalue_line("markers", "requires_noto_lite: test requires NotoEmoji[wght].ttf")
    config.addinivalue_line("markers", "requires_output_color: test requires built Color output")
    config.addinivalue_line("markers", "requires_output_lite: test requires built Lite output")


@pytest.fixture(scope="session")
def sarasa_font():
    if not _SARASA_REGULAR.exists():
        pytest.skip(f"Sarasa font not found: {_SARASA_REGULAR}")
    from fontTools.ttLib import TTFont
    font = TTFont(str(_SARASA_REGULAR))
    yield font
    font.close()


@pytest.fixture(scope="session")
def noto_color_emoji_font():
    if not _NOTO_COLOR_EMOJI.exists():
        pytest.skip(f"NotoColorEmoji not found: {_NOTO_COLOR_EMOJI}")
    from fontTools.ttLib import TTFont
    font = TTFont(str(_NOTO_COLOR_EMOJI))
    yield font
    font.close()


@pytest.fixture(scope="session")
def noto_emoji_font():
    if not _NOTO_EMOJI.exists():
        pytest.skip(f"NotoEmoji[wght].ttf not found: {_NOTO_EMOJI}")
    from fontTools.ttLib import TTFont
    font = TTFont(str(_NOTO_EMOJI))
    yield font
    font.close()


@pytest.fixture(scope="session")
def output_color_regular():
    if not _OUTPUT_COLOR_REGULAR.exists():
        pytest.skip(f"Color output not found: {_OUTPUT_COLOR_REGULAR}")
    from fontTools.ttLib import TTFont
    font = TTFont(str(_OUTPUT_COLOR_REGULAR))
    yield font
    font.close()


@pytest.fixture(scope="session")
def output_lite_regular():
    if not _OUTPUT_LITE_REGULAR.exists():
        pytest.skip(f"Lite output not found: {_OUTPUT_LITE_REGULAR}")
    from fontTools.ttLib import TTFont
    font = TTFont(str(_OUTPUT_LITE_REGULAR))
    yield font
    font.close()
