from datetime import datetime
from typing import Optional

from repositories.sync_pair_repository import SyncPairRepository
from repositories.sync_state_repository import SyncStateRepository
from utils.logging_config import logger


class SyncEngine:

    def __init__(self, sync_service, factory=None):
        """
        Args:
            sync_service: Business-logic service that performs the actual sync.
            factory:      Optional ServiceFactory used to look up individual
                          services by environment name for change detection.
                          When None, the skip-if-unchanged check is disabled
                          and every enabled pair always runs.
        """
        self.sync_service = sync_service
        self.factory = factory
        self.sync_pair_repository = SyncPairRepository()
        self.state_repo = SyncStateRepository()

    # ── Public entry points ──────────────────────────────────────────────────

    def run(self) -> None:
        pairs = self.sync_pair_repository.get_enabled()
        logger.info("Found %s enabled sync pairs", len(pairs))

        for pair in pairs:
            self.run_pair(pair)

    def run_pair(self, pair) -> None:
        logger.info(
            "Running sync '%s' (%s)",
            pair.name,
            pair.direction,
        )

        try:
            if self._should_skip(pair):
                logger.info(
                    "Skipping sync '%s': no changes detected since last run",
                    pair.name,
                )
                return

            self._dispatch(pair)

            logger.info("Sync completed successfully: %s", pair.name)
            self.state_repo.mark_synced(pair.name)

        except Exception:
            logger.exception("Sync failed: %s", pair.name)

    # ── Skip logic ───────────────────────────────────────────────────────────

    def _should_skip(self, pair) -> bool:
        """Return True only when BOTH source and target are unchanged since last sync.

        Behaviour when uncertain (no factory, no timestamp, lookup error):
        always returns False so the sync runs — safe-by-default.
        """
        if self.factory is None:
            return False

        last_synced_at: Optional[datetime] = self.state_repo.get_last_synced(pair.name)

        if last_synced_at is None:
            # Never synced before — always execute.
            return False

        source_mtime = self._get_modified_time(
            pair.source_environment, pair.source_group
        )
        target_mtime = self._get_modified_time(
            pair.target_environment, pair.target_group
        )

        if source_mtime is None or target_mtime is None:
            # Could not determine change times — run to be safe.
            logger.debug(
                "Could not determine modified times for pair '%s', will run sync",
                pair.name,
            )
            return False

        source_unchanged = source_mtime <= last_synced_at
        target_unchanged = target_mtime <= last_synced_at

        logger.debug(
            "Change detection | pair=%s | source_mtime=%s | target_mtime=%s"
            " | last_synced=%s | source_unchanged=%s | target_unchanged=%s",
            pair.name,
            source_mtime.isoformat(),
            target_mtime.isoformat(),
            last_synced_at.isoformat(),
            source_unchanged,
            target_unchanged,
        )

        return source_unchanged and target_unchanged

    def _get_modified_time(
        self, environment_name: str, group_name: str
    ) -> Optional[datetime]:
        """Retrieve group modified time from the appropriate service."""
        try:
            service = self.factory.get(environment_name)
            return service.get_group_modified_time(group_name)
        except Exception:
            logger.warning(
                "Could not get modified time | env=%s | group=%s",
                environment_name,
                group_name,
                exc_info=True,
            )
            return None

    # ── Dispatch sync direction ──────────────────────────────────────────────

    def _dispatch(self, pair) -> None:
        if pair.direction == "AD_TO_LDS":
            self.sync_service.sync_ad_to_lds(
                pair.source_group, pair.target_group
            )
        elif pair.direction == "LDS_TO_AD":
            self.sync_service.sync_lds_to_ad(
                pair.source_group, pair.target_group
            )
        elif pair.direction == "ENTRA_TO_AD":
            self.sync_service.sync_entraid_to_ad(
                pair.source_group, pair.target_group
            )
        elif pair.direction == "AD_TO_ENTRA":
            self.sync_service.sync_ad_to_entraid(
                pair.source_group, pair.target_group
            )
        elif pair.direction == "AD_TO_AD":
            self.sync_service.sync_ad_groups(
                pair.source_group, pair.target_group
            )
        else:
            raise ValueError(f"Unsupported direction: {pair.direction}")