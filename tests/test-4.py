from services.ldap_service import LDAPService
from services.service_factory import ServiceFactory

GROUP_NAME = "Python-Test-Group-4"


def run():

    ldap = ServiceFactory().get("AD_DF2")

    group_dn = ldap.get_group_dn(GROUP_NAME)

    if not group_dn:
        print(f"Group {GROUP_NAME} not found.")
        return

    members = ldap.get_group_members(GROUP_NAME)

    if not members:
        print("Group has no members.")
        return

    ldap.remove_members_from_group(
        group_dn,
        list(members)
    )

    print(
        f"Removed {len(members)} members from {GROUP_NAME}."
    )