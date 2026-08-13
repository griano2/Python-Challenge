from ldap3 import Connection, Server, Tls, MODIFY_ADD, MODIFY_DELETE
import os
import ssl

def getenv(name: str) -> str:
    """Return the value of an environment variable or an empty string if it is missing."""
    value = os.getenv(name)
    if value is None:
        print(f"Warning: environment variable '{name}' is not set.")
        return ""
    return value


def make_server(hostname: str, port: int = 636, timeout: int = 10) -> Server:
    """Create an LDAP server object configured for SSL/TLS."""
    tls = Tls(validate=ssl.CERT_NONE)
    return Server(
        hostname,
        port=port,
        connect_timeout=timeout,
        use_ssl=True,
        tls=tls,
        get_info="ALL",
    )


def bind(server: Server, username: str, password: str) -> Connection:
    """Bind to the LDAP server using the given service account credentials."""
    connection = Connection(
        server,
        user=username,
        password=password,
        auto_bind=True,
    )
    print("Connection successful:", connection.bound)
    return connection


def search(connection: Connection, search_base: str, search_filter: str, attributes: list, size_limit: int = 0):
    """Perform an LDAP search and return the entries."""
    successful = connection.search(
        search_base=search_base,
        search_filter=search_filter,
        attributes=attributes,
        size_limit=size_limit,
    )

    print("Search successful:", successful)
    return connection.entries


def print_members(entries, group_name: str) -> list:
    """Print the members of a group from LDAP search entries."""
    if not entries:
        print(f"No entries found for group '{group_name}'.")
        return []

    entry = entries[0]
    members = entry["member"].values
    if not members:
        print(f"Group '{group_name}' does not contain any members.")
        return []
    
    print(f"Members of {group_name}:")
    for dn in members:
        print(" -", dn)
    return members


def get_dn(entries, group_name: str) -> str:
    """Extract the distinguished name (DN) of a group from LDAP search entries."""
    if not entries:
        raise ValueError(f"No entries found for group '{group_name}'")
    return entries[0].entry_dn


def get_group_members(connection: Connection, search_base: str, group_name: str, filter_attribute: str, attributes: list[str] | tuple[str, ...] = ("member",), size_limit: int = 0) -> list:
    """Search a group and return its member list."""
    filter_value = f"({filter_attribute}={group_name})"
    entries = search(
        connection,
        search_base=search_base,
        search_filter=filter_value,
        attributes=list(attributes),
        size_limit=size_limit,
    )

    if not entries:
        print(f"No entries found for group '{group_name}'.")
        return []

    return print_members(entries, group_name)


def add_members_to_group(connection: Connection, target_dn: str, members: list) -> None:
    """Add each member to the target group."""
    for member in members:
        connection.modify(
            target_dn,
            {
                "member": [(MODIFY_ADD, [member])],
            },
        )
        print("Modify result:", connection.result)
        if connection.result["result"] == 0:
            print(f"Added {member} to the target group.")
        else:
            print(f"Error adding {member}: {connection.result}")


def remove_members_from_group(connection: Connection, target_dn: str, members: list) -> None:
    """Remove each member from the target group."""
    for member in members:
        connection.modify(
            target_dn,
            {
                "member": [(MODIFY_DELETE, [member])],
            },
        )
        print("Modify result:", connection.result)
        if connection.result["result"] == 0:
            print(f"Removed {member} from the target group.")
        else:
            print(f"Error removing {member}: {connection.result}")


def main() -> None:
    """Main execution flow for LDAP group member retrieval and management."""
    svc_ac = getenv("svc_ac")
    svc_pw = getenv("svc_pw")

    if not svc_ac or not svc_pw:
        print("Error: Missing LDAP service account credentials. Set svc_ac and svc_pw as environment variables.")
        return

    server = make_server("dir-tst.slb-tst.com")
    connection = bind(server, svc_ac, svc_pw)

    default_naming_context = server.info.other.get("defaultNamingContext")
    print("Default Naming Context:", default_naming_context)

    source_group = "Python-Test-Group-1"
    target_group = "Python-Test-Group-2"
    search_base = "DC=dir-tst,DC=slb-tst,DC=com"

    while True:
        print("\n=== LDAP Menu ===")
        print("1) Read users from the source group")
        print("2) Read users from the target group")
        print("3) Add users from the source group to the target group")
        print("4) Delete users from the target group")
        print("5) Exit")

        option = input("Select an option: ").strip()

        if option == "1":
            print(f"\nSource group: {source_group}")
            get_group_members(connection, search_base, source_group, "name")

        elif option == "2":
            print(f"\nTarget group: {target_group}")
            get_group_members(connection, search_base, target_group, "name")

        elif option == "3":
            source_members = get_group_members(connection, search_base, source_group, "name")
            if not source_members:
                print(f"No members to add from '{source_group}'.")
                continue

            target_entries = search(
                connection,
                search_base=search_base,
                search_filter=f"(cn={target_group})",
                attributes=["distinguishedName"],
                size_limit=1,
            )
            if not target_entries:
                print(f"Error: target group '{target_group}' not found.")
                continue

            target_dn = get_dn(target_entries, target_group)
            add_members_to_group(connection, target_dn, source_members)

        elif option == "4":
            target_entries = search(
                connection,
                search_base=search_base,
                search_filter=f"(cn={target_group})",
                attributes=["distinguishedName"],
                size_limit=1,
            )
            if not target_entries:
                print(f"Error: target group '{target_group}' not found.")
                continue

            target_dn = get_dn(target_entries, target_group)

            target_members = search(
                connection,
                search_base=search_base,
                search_filter=f"(cn={target_group})",
                attributes=["member"],
                size_limit=1,
            )
            members_to_remove = print_members(target_members, target_group)
            if not members_to_remove:
                print(f"The target group '{target_group}' has no users to delete.")
                continue

            remove_members_from_group(connection, target_dn, members_to_remove)

        elif option == "5":
            print("Exiting the program.")
            break

        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    main()
