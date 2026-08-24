from ldap3 import Connection, Server, Tls, MODIFY_ADD, MODIFY_DELETE, SUBTREE
from utils.audit import audit_log
from utils.logging_config import logger
from services.vault_service import VaultService
import ssl

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
        logger.info(
            "EVQ service initialized | host=%s | search_base=%s",
            "evq.lds.slb.com",
            self.search_base
        )
        
    def make_server(
            self, 
            hostname: str, 
            port: int = 636, 
            timeout: int = 10
        ) -> Server:
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

    def bind(
            self, 
            server: Server, 
            username: str, 
            password: str
        ) -> Connection:
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

    def search(
        self,
        search_filter,
        attributes,
        size_limit=0,
        search_base=None,
    ):
        search_base = search_base or self.search_base

        logger.debug(
            "LDAP search | base=%s | filter=%s | attributes=%s",
            search_base,
            search_filter,
            attributes,
        )

        self.connection.search(
            search_base=search_base,
            search_filter=search_filter,
            attributes=attributes,
            size_limit=size_limit,
        )

        logger.debug(
            "LDAP search complete | entries=%s",
            len(self.connection.entries),
        )

        return self.connection.entries

    def add_members_to_group(
            self, 
            group_alias: str, 
            member_dns: list[str]
        ) -> bool:
        group_dn = self.get_group_dn(group_alias)
        if not member_dns:
            logger.info(
                "No members to add | group=%s",
                group_alias
            )
            return True

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
            logger.info(
                "Group add successful | group=%s | members_added=%s",
                group_alias,
                len(member_dns)
            )

        else:
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
            logger.error(
                "Group add failed | group=%s | result=%s",
                group_alias,
                self.connection.result
            )

            return False

        return True

    def remove_members_from_group(
            self,
            group_alias: str,
            member_dns: list[str]
        ) -> bool:
        if not member_dns:
            logger.info(
                "No members to remove | group=%s",
                group_alias
            )
            return True
        
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
            logger.info(
                "Group remove successful | group=%s | members_removed=%s",
                group_alias,
                len(member_dns)
            )

        else:
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
            logger.error(
                "Group remove failed | group=%s | result=%s",
                group_alias,
                self.connection.result
            )

            return False

        return True

    def get_group_members(
        self,
        group_alias: str
    ) -> set[str]:
        self.connection.search(
            search_base="O=slb,C=an",
            search_filter=f"(alias={group_alias})",
            search_scope=SUBTREE,
            attributes=["cn", "uniqueMember"]
        )

        if not self.connection.entries:

            logger.warning(
                "Group not found | group=%s",
                group_alias
            )

            return set()

        group = self.connection.entries[0]

        if not hasattr(group, "uniqueMember"):

            logger.info(
                "Group has no members | group=%s",
                group_alias
            )

            return set()

        members = set(
            group.uniqueMember.values
        )

        logger.info(
            "Retrieved unique members | group=%s | count=%s",
            group_alias,
            len(members)
        )

        return members

    def find_user_by_id(
        self,
        directory_id: str,
    ) -> str | None:

        entries = self.search(
            search_base="O=slb,C=an",
            search_filter=f"(ID={directory_id})",
            attributes=["distinguishedName", "ID"],
            size_limit=1,
        )

        if not entries:
            logger.warning(
                "User not found | id=%s",
                directory_id,
            )
            return None

        return entries[0].entry_dn

    def get_group_dn(
        self,
        group_alias: str
    ) -> str | None:

        self.connection.search(
            search_base="O=slb,C=an",
            search_filter=f"(alias={group_alias})",
            search_scope=SUBTREE,
            attributes=["cn"]
        )

        if not self.connection.entries:

            logger.warning(
                "Group DN not found | group=%s",
                group_alias
            )

            return None

        group_dn = (
            self.connection.entries[0]
            .entry_dn
        )

        logger.debug(
            "Group DN resolved | group=%s | dn=%s",
            group_alias,
            group_dn
        )

        return group_dn