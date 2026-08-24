from ldap3 import Connection, Server, Tls, MODIFY_ADD, MODIFY_DELETE
from utils.audit import audit_log
from utils.logging_config import logger
from services.vault_service import VaultService
import ssl

class LDAPService:

    def __init__(self):
        vault = VaultService()
        username, password = vault.get_ad_creds()
        server = self.make_server("dir-tst.slb-tst.com")
        self.connection = self.bind(server, username, password)
        self.search_base = "DC=dir-tst,DC=slb-tst,DC=com"
        logger.info(
            "LDAP service initialized | host=%s | search_base=%s",
            "dir-tst.slb-tst.com",
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

    def get_group_members(
        self,
        group_name: str,
        filter_attribute: str = "name",
        attributes: list[str] | tuple[str, ...] = ("member",),
        size_limit: int = 0,
    ) -> set:

        filter_value = f"({filter_attribute}={group_name})"

        entries = self.search(
            search_filter=filter_value,
            attributes=list(attributes),
            size_limit=size_limit,
        )

        if not entries:
            logger.warning(
                "Group not found | group=%s",
                group_name
            )
            return set()

        entry = entries[0]

        if "member" not in entry:
            logger.info(
                "Group has no members | group=%s",
                group_name
            )
            return set()

        members = set(entry["member"].values)

        logger.info(
            "Retrieved group members | group=%s | count=%s",
            group_name,
            len(members)
        )

        return members

    def get_group_dn(
        self,
        group_name: str
    ):
        entries = self.search(
            search_filter=f"(cn={group_name})",
            attributes=["distinguishedName"],
            size_limit=1,
        )

        if not entries:

            logger.warning(
                "Group DN not found | group=%s",
                group_name
            )

            return None

        group_dn = entries[0].entry_dn

        logger.debug(
            "Group DN resolved | group=%s | dn=%s",
            group_name,
            group_dn
        )

        return group_dn

    def add_members_to_group(
        self,
        target_dn: str,
        members: list
    ) -> bool:

        if not members:

            logger.info(
                "No members to add | group=%s",
                target_dn
            )

            return True

        failed_members = []

        for member in members:

            self.connection.modify(
                target_dn,
                {
                    "member": [
                        (
                            MODIFY_ADD,
                            [member]
                        )
                    ],
                },
            )

            if self.connection.result["result"] == 0:

                audit_log(
                    action="ADD",
                    user_dn=member,
                    group_dn=target_dn,
                    success=True
                )

                logger.info(
                    "User added to group | user=%s | group=%s",
                    member,
                    target_dn
                )

            else:

                failed_members.append(member)

                logger.error(
                    "Failed to add user to group | user=%s | group=%s | result=%s",
                    member,
                    target_dn,
                    self.connection.result
                )

                audit_log(
                    action="ADD",
                    user_dn=member,
                    group_dn=target_dn,
                    success=False,
                    details=str(
                        self.connection.result
                    )
                )

        logger.info(
            "Group add operation completed | group=%s | attempted=%s",
            target_dn,
            len(members)
        )

        return not failed_members

    def remove_members_from_group(
        self,
        target_dn: str,
        members: list
    ) -> bool:

        if not members:

            logger.info(
                "No members to remove | group=%s",
                target_dn
            )

            return True

        failed_members = []

        for member in members:

            self.connection.modify(
                target_dn,
                {
                    "member": [
                        (
                            MODIFY_DELETE,
                            [member]
                        )
                    ],
                },
            )

            if self.connection.result["result"] == 0:

                audit_log(
                    action="REMOVE",
                    user_dn=member,
                    group_dn=target_dn,
                    success=True,
                )

                logger.info(
                    "User removed from group | user=%s | group=%s",
                    member,
                    target_dn
                )

            else:

                failed_members.append(member)

                logger.error(
                    "Failed to remove user from group | user=%s | group=%s | result=%s",
                    member,
                    target_dn,
                    self.connection.result,
                )

                audit_log(
                    action="REMOVE",
                    user_dn=member,
                    group_dn=target_dn,
                    success=False,
                    details=str(
                        self.connection.result
                    )
                )

        logger.info(
            "Group remove operation completed | group=%s | attempted=%s",
            target_dn,
            len(members)
        )

        return not failed_members

    def find_user_by_upn(
        self,
        email: str
    ) -> str | None:

        search_filter = (
            f"(|"
            f"(mail={email})"
            f"(userPrincipalName={email})"
            f")"
        )

        entries = self.search(
            search_filter=search_filter,
            attributes=[
                "distinguishedName",
                "mail",
                "sAMAccountName",
                "userPrincipalName"
            ],
            size_limit=10,
        )

        if not entries:

            logger.warning(
                "User not found | email=%s",
                email
            )

            return None

        user = entries[0]

        logger.info(
            "User lookup successful | email=%s | dn=%s",
            email,
            user.entry_dn
        )

        return user.entry_dn

    def find_upn_by_dn(
        self,
        user_dn: str
    ) -> str | None:

        entries = self.search(
            search_base=user_dn,
            search_filter="(objectClass=*)",
            attributes=["userPrincipalName"],
            size_limit=1,
        )

        if not entries or "userPrincipalName" not in entries[0]:
            logger.warning(
                "User UPN not found | dn=%s",
                user_dn
            )
            return None

        upn = entries[0]["userPrincipalName"].value

        logger.info(
            "User UPN lookup successful | dn=%s | upn=%s",
            user_dn,
            upn
        )

        return upn

    def find_user_by_uid(
        self,
        uid: str
    ) -> str | None:

        entries = self.search(
                search_filter=f"(uidNumber={uid})",
                attributes=["distinguishedName"],
                size_limit=1,
            )

        if not entries:
            logger.warning(
                "User not found | uid=%s",
                uid
            )
            return None

        user = entries[0]

        logger.info(
            "User lookup successful | uid=%s | dn=%s",
            uid,
            user.entry_dn
        )

        return user.entry_dn
