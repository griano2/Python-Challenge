from services.ldap_service import LDAPService

GROUP_NAME = "Python-Test-Group-1"

USERS = [
    "ADM-JPena49@slb-tst.com",
    "Adm-griano2@slb-tst.com",
    "Adm-jcastano5@slb-tst.com",
    "NEfendi@slb-tst.com",
    "MBXHoustonAP@slb-tst.com",
]


def run():

    ldap = LDAPService()

    group_dn = ldap.get_group_dn(GROUP_NAME)

    if not group_dn:
        print(f"Group {GROUP_NAME} not found.")
        return

    users_to_add = []

    for email in USERS:
        user_dn = ldap.find_user_by_upn(email)

        if user_dn:
            users_to_add.append(user_dn)

    ldap.add_members_to_group(
        group_dn,
        users_to_add
    )

    print("Add test completed.")