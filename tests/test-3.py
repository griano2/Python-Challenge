from services.ldap_service import LDAPService

GROUP_NAME = "Python-Test-Group-1"


def run():

    ldap = LDAPService()

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