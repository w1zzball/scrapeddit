import scrapeddit.utils.console as console_utils
from unittest.mock import MagicMock


def test_set_console():
    mock_console = MagicMock()

    console_utils.set_console(mock_console)
    assert console_utils.get_console() is mock_console


def test_get_console():
    default_console = console_utils.get_console()
    assert default_console is console_utils.console
