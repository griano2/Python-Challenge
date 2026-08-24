from services.ldap_service import LDAPService
from services.evq_service import EVQLDAPService

AD_GROUPS = [
    "Python-Test-Group-2",
    "Python-Test-Group-4",
]
EVQ_GROUP = "Other_Python-Test-Group-6"


def clear_ad_group(ldap: LDAPService, group_name: str) -> None:
    group_dn = ldap.get_group_dn(group_name)

    if not group_dn:
        print(f"Group not found: {group_name}")
        return

    members = ldap.get_group_members(group_name)

    if not members:
        print(f"Group has no members: {group_name}")
        return

    succeeded = ldap.remove_members_from_group(
        group_dn,
        list(members),
    )

    if succeeded:
        print(f"Removed {len(members)} members from {group_name}.")
    else:
        print(f"Failed to remove one or more members from {group_name}.")


def clear_evq_group(evq: EVQLDAPService, group_alias: str) -> None:
    members = evq.get_group_members(group_alias)

    if not members:
        print(f"Group has no members or was not found: {group_alias}")
        return

    succeeded = evq.remove_members_from_group(
        group_alias,
        list(members),
    )

    if succeeded:
        print(f"Removed {len(members)} members from {group_alias}.")
    else:
        print(f"Failed to remove one or more members from {group_alias}.")


def run() -> None:
    ldap = LDAPService()
    evq = EVQLDAPService()

    for group_name in AD_GROUPS:
        clear_ad_group(ldap, group_name)

    clear_evq_group(evq, EVQ_GROUP)
    print("Finished.")


if __name__ == "__main__":
    run()
