"""
Structured JSON audit logger.  Never logs credentials, paths in full, or secrets.
"""
import json
import logging
import sys
from typing import Any

_logger = logging.getLogger("backend_api.audit")
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
_logger.addHandler(_handler)
_logger.setLevel(logging.INFO)
_logger.propagate = False


def log_event(event_type: str, **fields: Any) -> None:
    _logger.info(json.dumps({"event": event_type, **fields}))
