from ldap3 import Connection, Server, Tls, MODIFY_ADD, MODIFY_DELETE, SUBTREE
from utils.audit import audit_log
from utils.logging_config import logger
from services.vault_service import VaultService
import ssl, re

class EVQLDAPService:

    def __init__(self):
        vault = VaultService()
        username, password = vault.get_lds_creds()
        server = self.make_server("evq.lds.slb.com")
        self.connection = self.bind(
            server,
            username,
            password
        )

        self.search_base = "OU=group,O=slb,C=an"
        
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

    def add_members_to_group(self, group_alias: str, member_dns: list[str]):
        group_dn = self.get_group_dn(group_alias)
        if not member_dns:
            return

        self.connection.modify(
            group_dn,
            {
                "uniqueMember": [
                    (
                        MODIFY_ADD,
                        member_dns
                    )
                ]
            }
        )

        if self.connection.result["result"] == 0:
            for member_dn in member_dns:
                audit_log(
                    action="ADD",
                    user_dn=member_dn,
                    group_dn=group_dn,
                    success=True
                )
            print(f"Added {len(member_dns)} members " f"to group.")

        else:
            logger.error(
                "Failed bulk add | group=%s | result=%s",
                group_dn,
                self.connection.result
            )

            for member_dn in member_dns:
                audit_log(
                    action="ADD",
                    user_dn=member_dn,
                    group_dn=group_dn,
                    success=False,
                    details=str(
                        self.connection.result
                    )
                )
            print(f"Error adding members: "f"{self.connection.result}")

    def remove_members_from_group(self, group_alias: str, member_dns: list[str]):
        if not member_dns:
            return
        group_dn = self.get_group_dn(group_alias)
        self.connection.modify(
            group_dn,
            {
                "uniqueMember": [
                    (
                        MODIFY_DELETE,
                        member_dns
                    )
                ]
            }
        )

        if self.connection.result["result"] == 0:
            for member_dn in member_dns:
                audit_log(
                    action="REMOVE",
                    user_dn=member_dn,
                    group_dn=group_dn,
                    success=True
                )
            print(f"Removed {len(member_dns)} members " f"from group.")

        else:
            logger.error(
                "Failed bulk remove | group=%s | result=%s",
                group_dn,
                self.connection.result
            )

            for member_dn in member_dns:
                audit_log(
                    action="REMOVE",
                    user_dn=member_dn,
                    group_dn=group_dn,
                    success=False,
                    details=str(
                        self.connection.result
                    )
                )
            print(f"Error removing members: " f"{self.connection.result}")

    def get_group_members(self, group_alias: str) -> set[str]:
        members = self.get_group_unique_members(group_alias)
        result = set()

        for member_dn in members:
            self.connection.search(
                search_base=member_dn,
                search_filter="(objectClass=*)",
                attributes=["activedirectorydn"]
            )

            if not self.connection.entries:
                continue

            user = self.connection.entries[0]
            if hasattr(user, "activedirectorydn"):
                result.add(user.activedirectorydn.value)
        return result

    def get_group_unique_members(self, group_alias: str) -> set[str]:
        self.connection.search(
            search_base="O=slb,C=an",
            search_filter=f"(alias={group_alias})",
            search_scope=SUBTREE,
            attributes=["cn", "uniqueMember"]
        )
        
        if not self.connection.entries:
            print(f"Group not found: {group_alias}")
            return
        
        group = self.connection.entries[0]
        if not hasattr(group, "uniqueMember"):
            print("No members found")
            return

        return set(group.uniqueMember.values)

    def normalize_identity(self, dn: str) -> str:
        match = re.search(
            r"CN=([^,]+)",
            dn,
            re.IGNORECASE
        )

        if not match:
            return ""

        return match.group(1).strip().upper()

    def find_lds_user_by_ad_dn(self, ad_dn: str):
        match = re.search(r"CN=([^,]+)", ad_dn, re.IGNORECASE)
        if not match:
            return None

        cn = match.group(1).strip()
        self.connection.search(
            search_base="O=slb,C=an",
            search_filter=f"(cn={cn})",
            search_scope=SUBTREE,
            attributes=["cn"]
        )

        if not self.connection.entries:
            return None
        return self.connection.entries[0]

    def get_group_dn(self, group_alias: str) -> str | None:
        self.connection.search(
            search_base="O=slb,C=an",
            search_filter=f"(alias={group_alias})",
            search_scope=SUBTREE,
            attributes=["cn"]
        )

        if not self.connection.entries:
            print(
                f"Group not found: "
                f"{group_alias}"
            )
            return None

        return self.connection.entries[0].entry_dn