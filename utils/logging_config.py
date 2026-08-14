import logging
from logging.handlers import RotatingFileHandler

LOG_FILE = "ldap_group_management.log"

logger = logging.getLogger("ldap_audit")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    handler.setFormatter(formatter)
    logger.addHandler(handler)