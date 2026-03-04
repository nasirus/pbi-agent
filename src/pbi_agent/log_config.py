import logging
from pathlib import Path


def configure_logging(verbose: bool) -> None:
    console_level = logging.DEBUG if verbose else logging.INFO
    log_path = Path.cwd() / "pbi-agent-debug.log"

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[console_handler, file_handler],
        force=True,
    )

    logging.getLogger(__name__).debug("Debug log file: %s", log_path)
