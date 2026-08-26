from services.ldap_service import LDAPService
from ldap3 import MODIFY_DELETE, SUBTREE


def run():

    group_alias = "Other_Python-Test-Group-6"

    evq = LDAPService(host="evq.lds.slb.com", directory_type="LDS")

    evq.connection.search(
        search_base="O=slb,C=an",
        search_filter=f"(alias={group_alias})",
        search_scope=SUBTREE,
        attributes=["cn", "uniqueMember"]
    )

    if not evq.connection.entries:
        print(f"Group not found: {group_alias}")
        return

    group = evq.connection.entries[0]

    group_dn = group.entry_dn

    members = (
        list(group.uniqueMember.values)
        if hasattr(group, "uniqueMember")
        else []
    )

    print(f"Group: {group.cn.value}")
    print(f"DN: {group_dn}")
    print(f"Members found: {len(members)}")

    for member_dn in members:

        evq.connection.modify(
            group_dn,
            {
                "uniqueMember": [
                    (
                        MODIFY_DELETE,
                        [member_dn]
                    )
                ]
            }
        )

        result = evq.connection.result

        if result["result"] == 0:
            print(f"Removed: {member_dn}")
        else:
            print(f"FAILED: {member_dn}")
            print(result)

    print("\nFinished.")
