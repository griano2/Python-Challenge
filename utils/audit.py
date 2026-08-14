from .logging_config import logger


def audit_log(
    action: str,
    user_dn: str,
    group_dn: str,
    success: bool,
    details: str = "",
):

    logger.info(
        "AUDIT | action=%s | user=%s | group=%s | success=%s | details=%s",
        action,
        user_dn,
        group_dn,
        success,
        details,
    )