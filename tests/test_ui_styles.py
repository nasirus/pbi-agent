from pbi_agent.ui.formatting import TOOL_BORDER_STYLES
from pbi_agent.ui.styles import CHAT_APP_CSS


def test_web_search_tool_group_has_dedicated_color() -> None:
    assert "ToolGroup.tool-group-web-search" in CHAT_APP_CSS
    assert "border-left: thick #0EA5E9;" in CHAT_APP_CSS


def test_web_search_tool_item_has_dedicated_background() -> None:
    assert "ToolItem.tool-call-web-search" in CHAT_APP_CSS
    assert "background: #0EA5E9 14%;" in CHAT_APP_CSS


def test_web_search_color_differs_from_skill_knowledge() -> None:
    assert TOOL_BORDER_STYLES["web-search"] != TOOL_BORDER_STYLES["skill-knowledge"]
