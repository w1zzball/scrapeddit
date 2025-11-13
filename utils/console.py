from rich.console import Console

# shared console instance
console = Console()


def set_console(new_console: Console) -> None:
    """Replace the shared console instance."""
    global console
    console = new_console


def get_console() -> Console:
    """Return the shared console instance."""
    return console
