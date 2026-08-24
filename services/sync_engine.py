from repositories.sync_pair_repository import SyncPairRepository
from utils.logging_config import logger


class SyncEngine:

    def __init__(self, sync_service):
        self.sync_service = sync_service
        self.sync_pair_repository = SyncPairRepository()

    def run(self) -> None:
        pairs = self.sync_pair_repository.get_enabled()
        logger.info(
            "Found %s enabled sync pairs",
            len(pairs)
        )

        for pair in pairs:
            self.run_pair(pair)

    def run_pair(self, pair) -> None:
        logger.info(
            "Running sync '%s' (%s)",
            pair.name,
            pair.direction
        )

        try:
            if pair.direction == "AD_TO_LDS":
                self.sync_service.sync_ad_to_lds(
                    pair.source_group,
                    pair.target_group
                )
            elif pair.direction == "LDS_TO_AD":
                self.sync_service.sync_lds_to_ad(
                    pair.source_group,
                    pair.target_group
                )
            elif pair.direction == "ENTRA_TO_AD":
                self.sync_service.sync_entraid_to_ad(
                    pair.source_group,
                    pair.target_group
                )
            elif pair.direction == "AD_TO_ENTRA":
                self.sync_service.sync_ad_to_entraid(
                    pair.source_group,
                    pair.target_group
                )

            elif pair.direction == "AD_TO_AD":
                self.sync_service.sync_ad_groups(
                    pair.source_group,
                    pair.target_group
                )

            else:
                raise ValueError(
                    f"Unsupported direction: {pair.direction}"
                )

            logger.info(
                "Sync completed successfully: %s",
                pair.name
            )

        except Exception:
            logger.exception(
                "Sync failed: %s",
                pair.name
            )