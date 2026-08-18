from services.ldap_service import LDAPService

GROUP_NAME = "Python-Test-Group-4"

USERS = [
    "AIgoshkin@slb-tst.com",
    "AAzmir2@slb-tst.com",
    "AClaridge@slb-tst.com",
]


def run():

    ldap = LDAPService()

    group_dn = ldap.get_group_dn(GROUP_NAME)

    if not group_dn:
        print(f"Group '{GROUP_NAME}' not found.")
        return

    users_to_add = []

    for email in USERS:

        user_dn = ldap.find_user_by_email(email)

        if user_dn:
            users_to_add.append(user_dn)
        else:
            print(f"User not found: {email}")

    if not users_to_add:
        print("No valid users found.")
        return

    ldap.add_members_to_group(
        group_dn,
        users_to_add
    )

    print(
        f"\nCompleted. Attempted to add "
        f"{len(users_to_add)} users to {GROUP_NAME}."
    )


if __name__ == "__main__":
    run()