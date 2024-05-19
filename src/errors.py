import ankiutils
import ankiutils.errors
from aqt import gui_hooks
from aqt.qt import *

from .config import config
from .consts import consts
from .log import logger


def _on_profile_did_open() -> None:
    ankiutils.errors.setup_error_handler(consts, config, logger)


def setup_error_handler() -> None:
    gui_hooks.profile_did_open.append(_on_profile_did_open)
