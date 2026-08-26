from services.ldap_service import LDAPService
from services.service_factory import ServiceFactory

GROUP_NAME = "Python-Test-Group-1"

USERS = [
    "NEfendi@slb-tst.com",
    "MBXHoustonAP@slb-tst.com",
]


def run():

    ldap = ServiceFactory().get("AD_DF2")

    group_dn = ldap.get_group_dn(GROUP_NAME)

    if not group_dn:
        print(f"Group {GROUP_NAME} not found.")
        return

    users_to_remove = []

    for email in USERS:
        user_dn = ldap.find_user_by_upn(email)

        if user_dn:
            users_to_remove.append(user_dn)

    ldap.remove_members_from_group(
        group_dn,
        users_to_remove
    )

    print("Remove test completed.")