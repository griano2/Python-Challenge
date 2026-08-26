from services.ldap_service import LDAPService
from services.service_factory import ServiceFactory
from utils.logging_config import logger
from utils.audit import audit_log
import importlib, re

services = ServiceFactory()
ldap = services.get("AD_DF2")
entra = services.get("ENTRA_DF2")
evq = services.get("LDS_TEST")

def print_group_members():
    print("Which group do you want to see?")
    print("1) Python-Test-Group-1 (On-Premise)")
    print("2) Python-Test-Group-2 (On-Premise)")
    print("3) Python-Test-Group-4 (On-Premise)")
    print("4) Python-Test-Group-5 (On-Premise)")
    print("5) Other_Python-Test-Group-6 (LDS ENVQ)")
    option = input("Select a group: ").strip()

    if option == "1":
        get_group_members("Python-Test-Group-1")
    elif option == "2":
        get_group_members("Python-Test-Group-2")
    elif option == "3":
        get_group_members("Python-Test-Group-4")
    elif option == "4":
        get_group_members("Python-Test-Group-5") 
    elif option == "5":
        members = evq.get_group_members("Other_Python-Test-Group-6")

        for member in sorted(members):
            print(member)

def get_group_members(group_name: str):
    members = ldap.get_group_members(group_name)
    if not members:
        print(f"No members found for group '{group_name}'.")
        return

    for member in members:
        print(member)

def sync_ad_groups(source_group: str, target_group: str):

    logger.info(
        "Starting AD_TO_AD sync | source=%s | target=%s",
        source_group,
        target_group
    )

    source_members = ldap.get_group_members(source_group)
    target_members = ldap.get_group_members(target_group)

    members_to_add = list(source_members - target_members)
    members_to_remove = list(target_members - source_members)

    logger.info(
        "Delta calculated | source=%s | target=%s | add=%s | remove=%s",
        source_group,
        target_group,
        len(members_to_add),
        len(members_to_remove)
    )

    target_dn = ldap.get_group_dn(target_group)
    logger.info(
        "Target group resolved | group=%s | dn=%s",
        target_group,
        target_dn
    )

    additions_succeeded = ldap.add_members_to_group(
        target_dn,
        members_to_add
    )
    removals_succeeded = ldap.remove_members_from_group(
        target_dn,
        members_to_remove
    )

    if not additions_succeeded or not removals_succeeded:
        raise RuntimeError(
            "AD_TO_AD failed: one or more AD membership changes were rejected"
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
        action="SYNC_AD",
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

def sync_entraid_to_ad(source_group: str, target_group: str):

    logger.info(
        "Starting ENTRA_TO_AD sync | source=%s | target=%s",
        source_group,
        target_group
    )

    cloud_upns = entra.get_group_members(source_group)

    source_dns = set()
    for upn in cloud_upns:
        dn = ldap.find_user_by_upn(upn)
        if dn:
            source_dns.add(dn)
        else:
            logger.warning("No on-prem match for %s", upn)

    target_dns = ldap.get_group_members(target_group)

    members_to_add = list(source_dns - target_dns)
    members_to_remove = list(target_dns - source_dns)

    logger.info(
        "Delta calculated | source=%s | target=%s | add=%s | remove=%s",
        source_group,
        target_group,
        len(members_to_add),
        len(members_to_remove)
    )

    target_dn = ldap.get_group_dn(target_group)
    logger.info(
        "Target group resolved | group=%s | dn=%s",
        target_group,
        target_dn
    )

    additions_succeeded = ldap.add_members_to_group(
        target_dn,
        members_to_add
    )
    removals_succeeded = ldap.remove_members_from_group(
        target_dn,
        members_to_remove
    )

    if not additions_succeeded or not removals_succeeded:
        raise RuntimeError(
            "ENTRA_TO_AD failed: one or more AD membership changes were rejected"
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
        action="SYNC_ENTRAID",
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

def sync_ad_to_entraid(source_group: str, target_group: str):

    source_dn = ldap.get_group_dn(source_group)
    target_group_id = entra.get_group_id(target_group)

    if not source_dn or not target_group_id:
        raise ValueError(
            f"Cannot sync: source or target group not found | "
            f"source={source_group} | target={target_group}"
        )

    source_members = ldap.get_group_members(source_group)
    source_upns = {
        upn
        for member_dn in source_members
        if (upn := ldap.find_upn_by_dn(member_dn))
    }

    target_upns = entra.get_group_members(target_group)

    members_to_add = list(source_upns - target_upns)
    members_to_remove = list(target_upns - source_upns)

    additions_succeeded = entra.add_members_to_group(target_group, members_to_add)
    removals_succeeded = entra.remove_members_from_group(target_group, members_to_remove)

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
        source_alias: str,
        target_group: str
    ):

        logger.info(
            "Starting LDS_TO_AD sync | source=%s | target=%s",
            source_alias,
            target_group
        )

        source_members = evq.get_group_members(
            source_alias
        )

        source_ids = {
            member.split(",", 1)[0].split()[-1]
            for member in source_members
        }

        ad_source_members = {
            user_dn
            for directory_id in source_ids
            if (user_dn := ldap.find_user_by_uid(directory_id))
        }

        target_members = ldap.get_group_members(
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

        target_dn = ldap.get_group_dn(
            target_group
        )

        logger.info(
            "Target group resolved | group=%s | dn=%s",
            target_group,
            target_dn
        )

        additions_succeeded = ldap.add_members_to_group(
            target_dn,
            members_to_add
        )

        removals_succeeded = ldap.remove_members_from_group(
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
    source_group: str,
    target_alias: str,
):

    logger.info(
        "Starting AD_TO_LDS sync | source=%s | target=%s",
        source_group,
        target_alias,
    )

    ad_members = ldap.get_group_members(
        source_group
    )

    source_ids = {
        member.split(",", 1)[0].split()[-1]
        for member in ad_members
    }

    lds_source_members = {
        user_dn
        for directory_id in source_ids
        if (user_dn := evq.find_user_by_id(directory_id))
    }

    target_members = set(
        evq.get_group_members(target_alias)
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

    additions_succeeded = evq.add_members_to_group(
        target_alias,
        members_to_add,
    )

    removals_succeeded = evq.remove_members_from_group(
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

def main() -> None:

    while True:
        print()
        print("1) Run test file")
        print("2) Print group members")
        print("3) Sync on-premise groups (GRP1 -> GRP2)")
        print("4) Sync EntraID group with on-premise group (GRP3 -> GRP4)")
        print("5) Sync LDS EVQ group with on-premise group (GRP6 -> GRP5)")
        print("6) Sync on-premise group with LDS EVQ group  (GRP5 -> GRP6)")
        print("7) Sync on-premise group with EntraID group (GRP1 -> GRP3)")
        print("8) Test fcn")
        print("0) Exit")
        option = input("Select an option: ").strip()

        if option == "1":
            test_file = input("Type the file's name: ").strip()
            try:
                module = importlib.import_module(f"tests.{test_file}")
                module.run()
            except ModuleNotFoundError:
                print(f"Test '{test_file}' not found.")
            except Exception as ex:
                print(f"Error running test: {ex}")

        elif option == "2":
            print_group_members()

        elif option == "3":
            sync_ad_groups("Python-Test-Group-1", "Python-Test-Group-2")

        elif option == "4":
            sync_entraid_to_ad("Python-Test-Group-3", "Python-Test-Group-4")

        elif option == "5":
            sync_lds_to_ad("Other_testing-ldap-grpter","Python-Test-Group-5")
            
        elif option == "6":
            sync_ad_to_lds("Python-Test-Group-5", "Other_Python-Test-Group-6")
        
        elif option == "7":
            sync_ad_to_entraid("Python-Test-Group-4", "Python-Test-Group-3")

        elif option == "8":
            evq.find_user_by_id("1359602")

        elif option == "0":
            break
        

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Unhandled application error")
        raise