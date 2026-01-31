from .patches import patch_certifi

patch_certifi()

# ruff: noqa: E402
from .backend.server import init_server
from .errors import setup_error_handler
from .menu import add_menu


def init() -> None:
    setup_error_handler()
    add_menu()
    init_server()
