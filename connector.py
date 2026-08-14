from ldap3 import Connection, Server, Tls, MODIFY_ADD, MODIFY_DELETE
import os
import hvac
import ssl
import logging
from logging.handlers import RotatingFileHandler

LOG_FILE = "ldap_group_management.log"

logger = logging.getLogger("ldap_audit")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=5)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    handler.setFormatter(formatter)
    logger.addHandler(handler)


def audit_log(
        action: str,
        user_dn: str,
        group_dn: str,
        success: bool,
        details: str = "") -> None:
    """
    Centralized audit logging.
    Records who, what, when, where, and result.
    """
    logger.info(
        "AUDIT | action=%s | user=%s | group=%s | success=%s | details=%s",
        action,
        user_dn,
        group_dn,
        success,
        details,
    )


def getCreds() -> tuple[str, str]:

    token = os.getenv("rootToken")

    if token is None:
        logger.warning("Environment variable 'rootToken' is not set.")
        print("Warning: environment variable 'rootToken' is not set.")

    client = hvac.Client(url="http://127.0.0.1:8200", token=token)

    if not client.is_authenticated():
        logger.error("Vault authentication failed")
        raise Exception("Vault authentication failed")

    secret = client.secrets.kv.v2.read_secret_version(
        path="challenge/creds",
        mount_point="secret",
        raise_on_deleted_version=True)

    logger.info("Credentials successfully retrieved from Vault")

    return (secret["data"]["data"]["username"],
            secret["data"]["data"]["password"])


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
    """Bind to the LDAP server."""

    try:
        connection = Connection(
            server,
            user=username,
            password=password,
            auto_bind=True,
        )

        logger.info(
            "LDAP connection successful | user=%s | server=%s",
            username,
            server.host)

        print("Connection successful:", connection.bound)

        return connection

    except Exception:
        logger.exception(
            "LDAP connection failed | user=%s | server=%s",
            username,
            server.host)
        raise


def search(
        connection: Connection,
        search_base: str,
        search_filter: str,
        attributes: list,
        size_limit: int = 0):
    """Perform an LDAP search and return the entries."""

    connection.search(
        search_base=search_base,
        search_filter=search_filter,
        attributes=attributes,
        size_limit=size_limit,
    )

    return connection.entries


def print_members(connection, search_base, members, group_name: str) -> None:

    if not members:
        print(f"Group '{group_name}' does not contain any members.")
        return

    print(f"Members of {group_name}:")

    for dn in members:
        try:

            entries = search(
                connection,
                search_base=dn,
                search_filter="(objectClass=person)",
                attributes=[
                    "mail",
                    "sAMAccountName",
                    "userPrincipalName",
                    "displayName"],
                size_limit=1,
            )

            if entries:
                user = entries[0]

                display_name = user.displayName.value if "displayName" in user else ""

                email = user.mail.value if "mail" in user else "N/A"

                alias = user.sAMAccountName.value if "sAMAccountName" in user else "N/A"

                upn = user.userPrincipalName.value if "userPrincipalName" in user else "N/A"

                print(
                    f" - {display_name} | " f"alias={alias} | " f"email={email} | " f"upn={upn}")

            else:
                print(f" - {dn}")

        except Exception as ex:
            logger.exception("Failed reading user attributes for %s", dn)
            print(f" - {dn} (error reading attributes: {ex})")


def get_group_members(
    connection: Connection,
    search_base: str,
    group_name: str,
    filter_attribute: str,
    attributes: list[str] | tuple[str, ...] = ("member",),
    size_limit: int = 0,
) -> set:

    filter_value = f"({filter_attribute}={group_name})"

    entries = search(
        connection,
        search_base=search_base,
        search_filter=filter_value,
        attributes=list(attributes),
        size_limit=size_limit,
    )

    if not entries:
        logger.warning("No entries found for group '%s'", group_name)
        print(f"No entries found for group '{group_name}'.")
        return set()

    entry = entries[0]

    members = entry["member"].values

    return set(members)


def get_group_dn(connection: Connection, search_base: str, group_name: str):
    """Return group DN."""

    entries = search(
        connection,
        search_base=search_base,
        search_filter=f"(cn={group_name})",
        attributes=["distinguishedName"],
        size_limit=1,
    )

    if not entries:
        logger.warning("Group '%s' not found", group_name)
        print(f"Group '{group_name}' not found.")
        return None

    return entries[0].entry_dn


def add_members_to_group(
        connection: Connection,
        target_dn: str,
        members: list) -> None:

    for member in members:

        connection.modify(
            target_dn,
            {
                "member": [(MODIFY_ADD, [member])],
            },
        )

        if connection.result["result"] == 0:

            audit_log(
                action="ADD",
                user_dn=member,
                group_dn=target_dn,
                success=True)

            print(f"Added {member} to the target group.")

        else:

            logger.error(
                "Failed to add user to group | user=%s | "
                "group=%s | result=%s",
                member,
                target_dn,
                connection.result)

            audit_log(
                action="ADD",
                user_dn=member,
                group_dn=target_dn,
                success=False,
                details=str(
                    connection.result))

            print(f"Error adding {member}: " f"{connection.result}")


def remove_members_from_group(
        connection: Connection,
        target_dn: str,
        members: list) -> None:

    for member in members:

        connection.modify(
            target_dn,
            {
                "member": [(MODIFY_DELETE, [member])],
            },
        )

        if connection.result["result"] == 0:

            audit_log(
                action="REMOVE",
                user_dn=member,
                group_dn=target_dn,
                success=True)

            print(f"Removed {member} " f"from the target group.")

        else:

            logger.error(
                "Failed to remove user from group "
                "| user=%s | group=%s | result=%s",
                member,
                target_dn,
                connection.result,
            )

            audit_log(
                action="REMOVE",
                user_dn=member,
                group_dn=target_dn,
                success=False,
                details=str(
                    connection.result))

            print(f"Error removing {member}: " f"{connection.result}")


def find_user_by_email(connection, search_base, email):

    search_filter = f"(|" f"(mail={email})" f"(userPrincipalName={email})" f")"

    entries = search(
        connection,
        search_base=search_base,
        search_filter=search_filter,
        attributes=[
            "distinguishedName",
            "mail",
            "sAMAccountName",
            "userPrincipalName"],
        size_limit=10,
    )

    if not entries:
        logger.warning("No user found for %s", email)
        print(f"No user found for '{email}'")
        return None

    user = entries[0]

    print("\nFound user:")
    print(" DN:", user.entry_dn)
    print(" Alias:", getattr(user, "sAMAccountName", ""))
    print(" Mail:", getattr(user, "mail", ""))
    print(" UPN:", getattr(user, "userPrincipalName", ""))

    logger.info(
        "User lookup successful | email=%s | dn=%s",
        email,
        user.entry_dn)

    return user.entry_dn


def main() -> None:

    svc_ac, svc_pw = getCreds()

    if not svc_ac or not svc_pw:
        logger.error("Missing LDAP service credentials")
        print("Error: Missing LDAP service " "account credentials.")
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
        print("3) Add users from group1 to group2")
        print("4) Delete users from group2 that are not in group1")
        print("5) Delete all users from group2")
        print("6) Sync both groups")
        print("7) Add user to group by email")
        print("8) Remove user from group by email")
        print("9) Exit")

        option = input("Select an option: ").strip()

        if option == "1":

            members = get_group_members(
                connection, search_base, source_group, "name")

            print_members(connection, search_base, members, source_group)

        elif option == "2":

            members = get_group_members(
                connection, search_base, target_group, "name")

            print_members(connection, search_base, members, target_group)

        elif option == "3":

            sourcegrp_members = get_group_members(
                connection, search_base, source_group, "name")

            targetgrp_members = get_group_members(
                connection, search_base, target_group, "name")

            members_to_add = list(sourcegrp_members - targetgrp_members)

            logger.info("Bulk add started | count=%s", len(members_to_add))

            target_dn = get_group_dn(connection, search_base, target_group)

            add_members_to_group(connection, target_dn, members_to_add)

        elif option == "4":

            sourcegrp_members = get_group_members(
                connection, search_base, source_group, "name")

            targetgrp_members = get_group_members(
                connection, search_base, target_group, "name")

            members_to_remove = list(targetgrp_members - sourcegrp_members)

            logger.info(
                "Bulk remove started | count=%s",
                len(members_to_remove))

            target_dn = get_group_dn(connection, search_base, target_group)

            remove_members_from_group(connection, target_dn, members_to_remove)

        elif option == "5":

            target_dn = get_group_dn(connection, search_base, target_group)

            members_to_remove = get_group_members(
                connection, search_base, target_group, "name")

            logger.info(
                "Full group cleanup started "
                "| count=%s",
                len(members_to_remove))

            remove_members_from_group(
                connection, target_dn, list(members_to_remove))

        elif option == "6":

            logger.info(
                "Group synchronization started | source=%s | target=%s",
                source_group,
                target_group)
            sourcegrp_members = get_group_members(
                connection, search_base, source_group, "name")
            targetgrp_members = get_group_members(
                connection, search_base, target_group, "name")

            members_to_add = list(sourcegrp_members - targetgrp_members)
            members_to_remove = list(targetgrp_members - sourcegrp_members)
            target_dn = get_group_dn(connection, search_base, target_group)

            add_members_to_group(connection, target_dn, members_to_add)
            remove_members_from_group(connection, target_dn, members_to_remove)

            logger.info(
                "Group synchronization completed | added=%s | removed=%s",
                len(members_to_add),
                len(members_to_remove))

        elif option == "7":

            email = input("User email: ").strip()

            print("Select group:")
            print(f"1) {source_group}")
            print(f"2) {target_group}")

            group_option = input("Group: ").strip()

            if group_option == "1":
                group_name = source_group
            elif group_option == "2":
                group_name = target_group
            else:
                print("Invalid group.")
                continue

            logger.info(
                "Manual add requested | email=%s | group=%s",
                email,
                group_name)

            user_dn = find_user_by_email(connection, search_base, email)
            if not user_dn:
                continue

            group_dn = get_group_dn(connection, search_base, group_name)
            add_members_to_group(connection, group_dn, [user_dn])

        elif option == "8":

            email = input("User email: ").strip()

            print("Select group:")
            print(f"1) {source_group}")
            print(f"2) {target_group}")

            group_option = input("Group: ").strip()

            if group_option == "1":
                group_name = source_group
            elif group_option == "2":
                group_name = target_group
            else:
                print("Invalid group.")
                continue

            logger.info(
                "Manual remove requested | email=%s | group=%s",
                email,
                group_name)

            user_dn = find_user_by_email(connection, search_base, email)
            if not user_dn:
                continue

            group_dn = get_group_dn(connection, search_base, group_name)
            remove_members_from_group(connection, group_dn, [user_dn])

        elif option == "9":
            logger.info("Application terminated by user")
            print("Exiting the program.")
            break

        else:
            print("Invalid option. Please try again.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Unhandled application error")
        raise
