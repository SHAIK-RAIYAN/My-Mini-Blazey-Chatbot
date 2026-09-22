import os
import sys
import logging

logging.getLogger("httpx").setLevel(logging.WARNING)

_logger = None

def get_logger() -> logging.Logger:
    global _logger
    if _logger is None:
        if hasattr(sys.stdout, "reconfigure"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
        _logger = logging.getLogger("blazeup_agent")
        _logger.setLevel(logging.INFO)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        if not _logger.handlers:
            formatter = logging.Formatter("[%(levelname)s] %(message)s")
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            _logger.addHandler(console_handler)
            backend_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_file = os.path.join(backend_root, "agent_production.log")
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            _logger.addHandler(file_handler)
    return _logger
