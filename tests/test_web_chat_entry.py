from __future__ import annotations

from unittest.mock import patch

from pbi_agent.web import chat_entry


def test_run_starts_watchdog_and_launches_chat() -> None:
    with (
        patch("pbi_agent.web.chat_entry._start_parent_watchdog") as mock_watchdog,
        patch("pbi_agent.web.chat_entry.main", return_value=7) as mock_main,
    ):
        rc = chat_entry.run(["--parent-pid", "4321", "--verbose"])

    assert rc == 7
    mock_watchdog.assert_called_once_with(4321)
    mock_main.assert_called_once_with(["--verbose", "chat"])
