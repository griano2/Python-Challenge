from ldap3 import Connection, Server, Tls, MODIFY_ADD, MODIFY_DELETE
from utils.audit import audit_log
from utils.logging_config import logger
from services.vault_service import VaultService
import ssl

class LDAPService:

    def __init__(self):
        vault = VaultService()
        username, password = vault.getCreds()
        server = self.make_server("dir-tst.slb-tst.com")
        self.connection = self.bind(server, username, password)
        self.search_base = "DC=dir-tst,DC=slb-tst,DC=com"

    def make_server(self, hostname: str, port: int = 636, timeout: int = 10) -> Server:
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

    def bind(self, server: Server, username: str, password: str) -> Connection:
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

            return connection

        except Exception:
            logger.exception(
                "LDAP connection failed | user=%s | server=%s",
                username,
                server.host)
            raise

    def search(self, search_filter, attributes, size_limit=0):
        self.connection.search(
            search_base=self.search_base,
            search_filter=search_filter,
            attributes=attributes,
            size_limit=size_limit,
        )

        return self.connection.entries

    def get_group_members(self, group_name: str, filter_attribute: str = "name", attributes: list[str] | tuple[str, ...] = ("member",),size_limit: int = 0,) -> set:

        filter_value = f"({filter_attribute}={group_name})"
        entries = self.search(
            search_filter=filter_value,
            attributes=list(attributes),
            size_limit=size_limit,
        )

        if not entries:
            logger.warning("No entries found for group '%s'", group_name)
            return set()

        entry = entries[0]

        if "member" not in entry:
            return set()

        members = entry["member"].values
        return set(members)

    def get_group_dn(self, group_name: str):
        """Return group DN."""

        entries = self.search(
            search_filter=f"(cn={group_name})",
            attributes=["distinguishedName"],
            size_limit=1,
        )

        if not entries:
            logger.warning("Group '%s' not found", group_name)
            print(f"Group '{group_name}' not found.")
            return None

        return entries[0].entry_dn

    def add_members_to_group(self, target_dn: str, members: list) -> None:

        for member in members:
            self.connection.modify(
                target_dn,
                {
                    "member": [(MODIFY_ADD, [member])],
                },
            )

            if self.connection.result["result"] == 0:
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
                    self.connection.result)

                audit_log(
                    action="ADD",
                    user_dn=member,
                    group_dn=target_dn,
                    success=False,
                    details=str(self.connection.result))

                print(f"Error adding {member}: " f"{self.connection.result}")

    def remove_members_from_group(self, target_dn: str, members: list) -> None:
        for member in members:
            self.connection.modify(
                target_dn,
                {
                    "member": [(MODIFY_DELETE, [member])],
                },
            )

            if self.connection.result["result"] == 0:
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
                    self.connection.result,
                )

                audit_log(
                    action="REMOVE",
                    user_dn=member,
                    group_dn=target_dn,
                    success=False,
                    details=str(self.connection.result))

                print(f"Error removing {member}: " f"{self.connection.result}")

    def find_user_by_email(self, email: str) -> str | None:

        search_filter = f"(|" f"(mail={email})" f"(userPrincipalName={email})" f")"

        entries = self.search(
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

        # print("\nFound user:")
        # print(" DN:", user.entry_dn)
        # print(" Alias:", getattr(user, "sAMAccountName", ""))
        # print(" Mail:", getattr(user, "mail", ""))
        # print(" UPN:", getattr(user, "userPrincipalName", ""))

        logger.info(
            "User lookup successful | email=%s | dn=%s",
            email,
            user.entry_dn)

        return user.entry_dn