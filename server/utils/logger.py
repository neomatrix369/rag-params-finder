import logging
import os
import sys

from server.utils.scope_log import ScopeFilter

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

_OPTION_A_FORMAT = "%(asctime)s - %(levelname)s - [rag-params-finder] [%(log_scope)s] %(message)s"

_handler = logging.StreamHandler(sys.stdout)
_handler.addFilter(ScopeFilter())
_handler.setFormatter(logging.Formatter(_OPTION_A_FORMAT))

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), handlers=[_handler])


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
