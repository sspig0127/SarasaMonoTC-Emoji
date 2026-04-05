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
OUTPUT_NERD_LITE_DIR = _ROOT / "output" / "fonts-nerd-lite"
OUTPUT_COLRV1_DIR = _ROOT / "output" / "fonts-colrv1"

sys.path.insert(0, str(_ROOT))
from build import find_font  # noqa: E402

_SARASA_REGULAR = find_font(FONTS_DIR, "SarasaMonoTC-Regular.ttf")
_NOTO_COLOR_EMOJI = find_font(FONTS_DIR, "NotoColorEmoji.ttf")
_NOTO_EMOJI = find_font(FONTS_DIR, "NotoEmoji[wght].ttf")
_NOTO_COLRV1 = find_font(FONTS_DIR, "Noto-COLRv1.ttf")
_NERD_FONT = find_font(FONTS_DIR, "SymbolsNerdFontMono-Regular.ttf")
_OUTPUT_COLOR_REGULAR = OUTPUT_COLOR_DIR / "SarasaMonoTCEmoji-Regular.ttf"
_OUTPUT_LITE_REGULAR = OUTPUT_LITE_DIR / "SarasaMonoTCEmojiLite-Regular.ttf"
_OUTPUT_NERD_LITE_REGULAR = OUTPUT_NERD_LITE_DIR / "SarasaMonoTCEmojiLiteNerd-Regular.ttf"
_OUTPUT_COLRV1_REGULAR = OUTPUT_COLRV1_DIR / "SarasaMonoTCEmojiCOLRv1-Regular.ttf"


def pytest_configure(config):
    config.addinivalue_line("markers", "requires_sarasa: test requires Sarasa source font")
    config.addinivalue_line("markers", "requires_noto_color: test requires NotoColorEmoji.ttf")
    config.addinivalue_line("markers", "requires_noto_lite: test requires NotoEmoji[wght].ttf")
    config.addinivalue_line("markers", "requires_noto_colrv1: test requires Noto-COLRv1.ttf")
    config.addinivalue_line("markers", "requires_nerd_font: test requires SymbolsNerdFontMono-Regular.ttf")
    config.addinivalue_line("markers", "requires_output_color: test requires built Color output")
    config.addinivalue_line("markers", "requires_output_lite: test requires built Lite output")
    config.addinivalue_line("markers", "requires_output_nerd_lite: test requires built Nerd Lite output")
    config.addinivalue_line("markers", "requires_output_colrv1: test requires built COLRv1 output")


@pytest.fixture(scope="session")
def sarasa_font():
    if _SARASA_REGULAR is None:
        pytest.skip("SarasaMonoTC-Regular.ttf not found under fonts/")
    from fontTools.ttLib import TTFont
    font = TTFont(str(_SARASA_REGULAR))
    yield font
    font.close()


@pytest.fixture(scope="session")
def noto_color_emoji_font():
    if _NOTO_COLOR_EMOJI is None:
        pytest.skip("NotoColorEmoji.ttf not found under fonts/")
    from fontTools.ttLib import TTFont
    font = TTFont(str(_NOTO_COLOR_EMOJI))
    yield font
    font.close()


@pytest.fixture(scope="session")
def noto_emoji_font():
    if _NOTO_EMOJI is None:
        pytest.skip("NotoEmoji[wght].ttf not found under fonts/")
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
def noto_colrv1_font():
    if _NOTO_COLRV1 is None:
        pytest.skip("Noto-COLRv1.ttf not found under fonts/")
    from fontTools.ttLib import TTFont
    font = TTFont(str(_NOTO_COLRV1))
    yield font
    font.close()


@pytest.fixture(scope="session")
def nerd_font():
    if _NERD_FONT is None:
        pytest.skip("SymbolsNerdFontMono-Regular.ttf not found under fonts/")
    from fontTools.ttLib import TTFont
    font = TTFont(str(_NERD_FONT))
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


@pytest.fixture(scope="session")
def output_nerd_lite_regular():
    if not _OUTPUT_NERD_LITE_REGULAR.exists():
        pytest.skip(f"Nerd Lite output not found: {_OUTPUT_NERD_LITE_REGULAR}")
    from fontTools.ttLib import TTFont
    font = TTFont(str(_OUTPUT_NERD_LITE_REGULAR))
    yield font
    font.close()


@pytest.fixture(scope="session")
def output_colrv1_regular():
    if not _OUTPUT_COLRV1_REGULAR.exists():
        pytest.skip(f"COLRv1 output not found: {_OUTPUT_COLRV1_REGULAR}")
    from fontTools.ttLib import TTFont
    font = TTFont(str(_OUTPUT_COLRV1_REGULAR))
    yield font
    font.close()
