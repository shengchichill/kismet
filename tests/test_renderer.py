from io import StringIO
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


def _make_console() -> Console:
    return Console(file=StringIO(), force_terminal=True, width=120)


def test_tarot_zh_has_all_22_cards():
    from kismet.agent.tools.renderer import _TAROT_ZH
    from kismet.agent.tools.divine import _MAJOR_ARCANA
    for card in _MAJOR_ARCANA:
        assert card in _TAROT_ZH, f"Missing Chinese name for: {card}"


def test_tarot_emoji_has_all_22_cards():
    from kismet.agent.tools.renderer import _TAROT_EMOJI
    from kismet.agent.tools.divine import _MAJOR_ARCANA
    for card in _MAJOR_ARCANA:
        assert card in _TAROT_EMOJI, f"Missing emoji for: {card}"


def test_make_card_panel_returns_panel():
    from kismet.agent.tools.renderer import _make_card_panel
    for state in ("facedown", "flipping", "revealed"):
        result = _make_card_panel("🌕", "月亮", "正位", state)
        assert isinstance(result, Panel)


def test_make_card_panel_renders_without_error():
    from kismet.agent.tools.renderer import _make_card_panel
    console = _make_console()
    for state in ("facedown", "flipping", "revealed"):
        panel = _make_card_panel("💀", "死神", "逆位", state)
        console.print(panel)  # must not raise


def test_make_spread_table_returns_table():
    from kismet.agent.tools.renderer import _make_spread_table
    card_data = [("🌕", "月亮", "正位"), ("💀", "死神", "逆位"), ("☀️", "太陽", "正位")]
    result = _make_spread_table(card_data, revealed={0, 1, 2}, flipping=set())
    assert isinstance(result, Table)


def test_make_spread_table_renders_without_error():
    from kismet.agent.tools.renderer import _make_spread_table
    console = _make_console()
    card_data = [("🌕", "月亮", "正位"), ("💀", "死神", "逆位"), ("☀️", "太陽", "正位")]
    for revealed, flipping in [
        (set(), set()),
        (set(), {0, 1, 2}),
        ({0}, {1, 2}),
        ({0, 1}, {2}),
        ({0, 1, 2}, set()),
    ]:
        table = _make_spread_table(card_data, revealed, flipping)
        console.print(table)


from unittest.mock import patch


@patch("kismet.agent.tools.renderer.time.sleep")
def test_show_divination_animation_8_frames(mock_sleep):
    from kismet.agent.tools.renderer import RendererTool
    renderer = RendererTool()
    renderer.console = _make_console()
    renderer.show_divination_animation("bf44a92cafe2f8", lucky_match="cafe")
    assert mock_sleep.call_count == 8


@patch("kismet.agent.tools.renderer.time.sleep")
def test_show_divination_animation_unlucky(mock_sleep):
    from kismet.agent.tools.renderer import RendererTool
    renderer = RendererTool()
    renderer.console = _make_console()
    renderer.show_divination_animation("3f7a404deadbeef", unlucky_match="dead")
    assert mock_sleep.call_count == 8


def test_altar_content_returns_renderable():
    from rich.console import Group
    from kismet.agent.tools.renderer import RendererTool
    renderer = RendererTool()
    content = renderer._altar_content()
    assert isinstance(content, Group)


def test_altar_content_renders_without_error():
    from kismet.agent.tools.renderer import RendererTool
    renderer = RendererTool()
    renderer.console = _make_console()
    for frame in range(4):
        renderer._altar_frame = frame
        renderer.console.print(renderer._altar_content())
