from services.ldap_service import LDAPService
from services.entraid_service import EntraIDService
from services.evq_service import EVQLDAPService
from utils.logging_config import logger
from utils.audit import audit_log


class SyncService:
    def __init__(self, ldap_service: LDAPService, entraid_service: EntraIDService, evq_service: EVQLDAPService):
        self.ldap = ldap_service
        self.entra = entraid_service
        self.evq = evq_service

    def sync_ad_groups(
        self,
        source_group: str,
        target_group: str
    ) -> None:

        logger.info(
            "Starting AD_TO_AD sync | source=%s | target=%s",
            source_group,
            target_group
        )

        try:

            source_dn = self.ldap.get_group_dn(
                source_group
            )

            target_dn = self.ldap.get_group_dn(
                target_group
            )

            if not source_dn or not target_dn:
                raise ValueError(
                    f"Cannot sync: source or target AD group not found | "
                    f"source={source_group} | target={target_group}"
                )

            source_members = self.ldap.get_group_members(
                source_group
            )

            target_members = self.ldap.get_group_members(
                target_group
            )

            members_to_add = list(
                source_members - target_members
            )

            members_to_remove = list(
                target_members - source_members
            )

            self.ldap.add_members_to_group(
                target_dn,
                members_to_add
            )

            self.ldap.remove_members_from_group(
                target_dn,
                members_to_remove
            )

            logger.info(
                "AD_TO_AD complete | source=%s | target=%s | source_members=%s | target_members=%s | add=%s | remove=%s",
                source_group,
                target_group,
                len(source_members),
                len(target_members),
                len(members_to_add),
                len(members_to_remove)
            )

            audit_log(
                action="SYNC_AD_TO_AD",
                user_dn=source_group,
                group_dn=target_group,
                success=True,
                details=(
                    f"source_members={len(source_members)};"
                    f"target_members={len(target_members)};"
                    f"add={len(members_to_add)};"
                    f"remove={len(members_to_remove)}"
                )
            )

        except Exception as ex:

            logger.exception(
                "AD_TO_AD failed | source=%s | target=%s",
                source_group,
                target_group
            )

            audit_log(
                action="SYNC_AD_TO_AD",
                user_dn=source_group,
                group_dn=target_group,
                success=False,
                details=str(ex)
            )

            raise

    def sync_entraid_to_ad(
        self,
        source_group: str,
        target_group: str
    ) -> None:

        logger.info(
            "Starting ENTRA_TO_AD sync | source=%s | target=%s",
            source_group,
            target_group
        )

        try:

            self.entra.get_group_id(
                source_group
            )

            target_dn = self.ldap.get_group_dn(
                target_group
            )

            if not target_dn:
                raise ValueError(
                    f"Cannot sync: target AD group not found | "
                    f"target={target_group}"
                )

            cloud_upns = self.entra.get_group_members(
                source_group
            )

            source_dns = set()

            for upn in cloud_upns:

                dn = self.ldap.find_user_by_upn(upn)

                if dn:
                    source_dns.add(dn)

                else:
                    logger.warning(
                        "No on-prem match for %s",
                        upn
                    )

            target_dns = self.ldap.get_group_members(
                target_group
            )

            members_to_add = list(
                source_dns - target_dns
            )

            members_to_remove = list(
                target_dns - source_dns
            )

            self.ldap.add_members_to_group(
                target_dn,
                members_to_add
            )

            self.ldap.remove_members_from_group(
                target_dn,
                members_to_remove
            )

            logger.info(
                "ENTRA_TO_AD complete | source=%s | target=%s | source_members=%s | target_members=%s | add=%s | remove=%s",
                source_group,
                target_group,
                len(cloud_upns),
                len(target_dns),
                len(members_to_add),
                len(members_to_remove)
            )

            audit_log(
                action="SYNC_ENTRA_TO_AD",
                user_dn=source_group,
                group_dn=target_group,
                success=True,
                details=(
                    f"source_members={len(cloud_upns)};"
                    f"target_members={len(target_dns)};"
                    f"add={len(members_to_add)};"
                    f"remove={len(members_to_remove)}"
                )
            )

        except Exception as ex:

            logger.exception(
                "ENTRA_TO_AD failed | source=%s | target=%s",
                source_group,
                target_group
            )

            audit_log(
                action="SYNC_ENTRA_TO_AD",
                user_dn=source_group,
                group_dn=target_group,
                success=False,
                details=str(ex)
            )

            raise

    def sync_ad_to_entraid(
            self,
            source_group: str,
            target_group: str):

        source_dn = self.ldap.get_group_dn(source_group)
        target_group_id = self.entra.get_group_id(target_group)

        if not source_dn or not target_group_id:
            raise ValueError(
                f"Cannot sync: source or target group not found | "
                f"source={source_group} | target={target_group}"
            )

        source_members = self.ldap.get_group_members(source_group)
        source_upns = {
            upn
            for member_dn in source_members
            if (upn := self.ldap.find_upn_by_dn(member_dn))
        }

        target_upns = self.entra.get_group_members(target_group)

        members_to_add = list(source_upns - target_upns)
        members_to_remove = list(target_upns - source_upns)

        additions_succeeded = self.entra.add_members_to_group(
            target_group,
            members_to_add
        )

        removals_succeeded = self.entra.remove_members_from_group(
            target_group,
            members_to_remove
        )

        if not additions_succeeded or not removals_succeeded:
            raise RuntimeError(
                "AD_TO_ENTRA failed: one or more EntraID membership changes were rejected"
            )

        audit_log(
            action="SYNC_AD_TO_ENTRA",
            user_dn=source_group,
            group_dn=target_group,
            success=True,
            details=(
                f"source_members={len(source_upns)};"
                f"target_members={len(target_upns)};"
                f"add={len(members_to_add)};"
                f"remove={len(members_to_remove)}"
            )
        )

    def sync_lds_to_ad(
            self,
            source_alias: str,
            target_group: str
        ):

            logger.info(
                "Starting LDS_TO_AD sync | source=%s | target=%s",
                source_alias,
                target_group
            )

            source_dn = self.evq.get_group_dn(
                source_alias
            )

            target_dn = self.ldap.get_group_dn(
                target_group
            )

            if not source_dn or not target_dn:
                raise ValueError(
                    f"Cannot sync: source or target group not found | "
                    f"source={source_alias} | target={target_group}"
                )

            source_members = self.evq.get_group_members(
                source_alias
            )

            source_ids = {
                member.split(",", 1)[0].split()[-1]
                for member in source_members
            }

            ad_source_members = {
                user_dn
                for directory_id in source_ids
                if (user_dn := self.ldap.find_user_by_uid(directory_id))
            }

            target_members = self.ldap.get_group_members(
                target_group
            )

            members_to_add = list(ad_source_members - target_members)
            members_to_remove = list(target_members - ad_source_members)

            logger.info(
                "Delta calculated | source=%s | target=%s | add=%s | remove=%s",
                source_alias,
                target_group,
                len(members_to_add),
                len(members_to_remove)
            )

            logger.info(
                "Target group resolved | group=%s | dn=%s",
                target_group,
                target_dn
            )

            additions_succeeded = self.ldap.add_members_to_group(
                target_dn,
                members_to_add
            )

            removals_succeeded = self.ldap.remove_members_from_group(
                target_dn,
                members_to_remove
            )

            if not additions_succeeded or not removals_succeeded:
                raise RuntimeError(
                    "LDS_TO_AD failed: one or more AD membership changes were rejected"
                )

            logger.info(
                "LDS_TO_AD complete | source=%s | target=%s | source_members=%s | target_members=%s | add=%s | remove=%s",
                source_alias,
                target_group,
                len(source_members),
                len(target_members),
                len(members_to_add),
                len(members_to_remove)
            )

            audit_log(
                action="SYNC_LDS_TO_AD",
                user_dn=source_alias,
                group_dn=target_group,
                success=True,
                details=(
                    f"source_members={len(source_members)};"
                    f"target_members={len(target_members)};"
                    f"add={len(members_to_add)};"
                    f"remove={len(members_to_remove)}"
                )
            )

    def sync_ad_to_lds(
        self,
        source_group: str,
        target_alias: str,
    ):

        logger.info(
            "Starting AD_TO_LDS sync | source=%s | target=%s",
            source_group,
            target_alias,
        )

        source_dn = self.ldap.get_group_dn(
            source_group
        )

        target_dn = self.evq.get_group_dn(
            target_alias
        )

        if not source_dn or not target_dn:
            raise ValueError(
                f"Cannot sync: source or target group not found | "
                f"source={source_group} | target={target_alias}"
            )

        ad_members = self.ldap.get_group_members(
            source_group
        )

        source_ids = {
            member.split(",", 1)[0].split()[-1]
            for member in ad_members
        }

        lds_source_members = {
            user_dn
            for directory_id in source_ids
            if (user_dn := self.evq.find_user_by_id(directory_id))
        }

        target_members = set(
            self.evq.get_group_members(target_alias)
        )

        members_to_add = list(
            lds_source_members - target_members
        )

        members_to_remove = list(
            target_members - lds_source_members
        )

        logger.info(
            "Delta calculated | source=%s | target=%s | add=%s | remove=%s",
            source_group,
            target_alias,
            len(members_to_add),
            len(members_to_remove),
        )

        additions_succeeded = self.evq.add_members_to_group(
            target_alias,
            members_to_add,
        )

        removals_succeeded = self.evq.remove_members_from_group(
            target_alias,
            members_to_remove,
        )

        if not additions_succeeded or not removals_succeeded:
            raise RuntimeError(
                "AD_TO_LDS failed: one or more LDS membership changes were rejected"
            )

        logger.info(
            "AD_TO_LDS complete | source=%s | target=%s | source_members=%s | target_members=%s | add=%s | remove=%s",
            source_group,
            target_alias,
            len(ad_members),
            len(target_members),
            len(members_to_add),
            len(members_to_remove),
        )

        audit_log(
            action="SYNC_AD_TO_LDS",
            user_dn=source_group,
            group_dn=target_alias,
            success=True,
            details=(
                f"source_members={len(ad_members)};"
                f"target_members={len(target_members)};"
                f"add={len(members_to_add)};"
                f"remove={len(members_to_remove)}"
            ),
        )