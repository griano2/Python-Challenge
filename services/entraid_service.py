import msal
import requests
from utils.audit import audit_log
from utils.logging_config import logger


class EntraIDService:

    def __init__(
        self,
        client_id: str,
        tenant_id: str = "organizations"
    ):
        self.app = msal.PublicClientApplication(
            client_id=client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
        )

        self.base_url = "https://graph.microsoft.com/v1.0"

        logger.info(
            "EntraIDService initialized | tenant=%s",
            tenant_id
        )

    def _get_token(self) -> str:

        accounts = self.app.get_accounts()

        if accounts:

            logger.debug(
                "Attempting silent token acquisition"
            )

            result = self.app.acquire_token_silent(
                scopes=["Group.ReadWrite.All"],
                account=accounts[0],
            )

            if result and "access_token" in result:
                logger.debug(
                    "EntraID token acquired silently"
                )
                return result["access_token"]

        logger.info(
            "Starting interactive EntraID authentication"
        )

        result = self.app.acquire_token_interactive(
            scopes=["Group.ReadWrite.All"],
        )

        if "access_token" not in result:

            logger.error(
                "EntraID authentication failed | details=%s",
                result.get("error_description")
            )

            raise Exception(
                f"Auth failed: "
                f"{result.get('error_description')}"
            )

        logger.info(
            "EntraID authentication successful"
        )

        return result["access_token"]

    def _get_headers(self) -> dict:

        return {
            "Authorization": f"Bearer {self._get_token()}"
        }

    def get_group_id(self, group_name: str) -> str:

        logger.info(
            "Searching EntraID group | group=%s",
            group_name
        )

        params = {
            "$filter": f"displayName eq '{group_name}'",
            "$select": "id,displayName",
        }

        resp = requests.get(
            f"{self.base_url}/groups",
            headers=self._get_headers(),
            params=params,
        )

        resp.raise_for_status()

        groups = resp.json().get("value", [])

        if not groups:

            logger.warning(
                "EntraID group not found | group=%s",
                group_name
            )

            raise Exception(
                f"Group '{group_name}' not found in EntraID"
            )

        group_id = groups[0]["id"]

        logger.info(
            "EntraID group found | group=%s | id=%s",
            group_name,
            group_id
        )

        return group_id

    def get_group_members(
        self,
        group_name: str
    ) -> set[str]:

        logger.info(
            "Retrieving EntraID group members | group=%s",
            group_name
        )

        group_id = self.get_group_id(group_name)

        members = set()

        url = f"{self.base_url}/groups/{group_id}/members"

        page_count = 0

        while url:

            params = {
                "$select": "userPrincipalName",
                "$top": 999
            }

            resp = requests.get(
                url,
                headers=self._get_headers(),
                params=params
            )

            resp.raise_for_status()

            data = resp.json()

            page_count += 1

            for item in data.get("value", []):

                user_principal_name = item.get(
                    "userPrincipalName"
                )

                if user_principal_name:
                    members.add(user_principal_name)

            url = data.get("@odata.nextLink")

        logger.info(
            "EntraID members retrieved | group=%s | count=%d | pages=%d",
            group_name,
            len(members),
            page_count
        )

        return members

    def find_user_id_by_upn(self, upn: str) -> str | None:
        response = requests.get(
            f"{self.base_url}/users/{upn}",
            headers=self._get_headers(),
            params={"$select": "id,userPrincipalName"},
        )

        if response.status_code == 404:
            logger.warning(
                "EntraID user not found | upn=%s",
                upn,
            )
            return None

        response.raise_for_status()
        return response.json()["id"]

    def add_members_to_group(
        self,
        group_name: str,
        upns: list[str],
    ) -> bool:
        if not upns:
            logger.info(
                "No users to add | group=%s",
                group_name,
            )
            return True

        group_id = self.get_group_id(group_name)
        failed = False

        for upn in upns:
            user_id = self.find_user_id_by_upn(upn)

            if not user_id:
                failed = True
                continue

            response = requests.post(
                f"{self.base_url}/groups/{group_id}/members/$ref",
                headers={
                    **self._get_headers(),
                    "Content-Type": "application/json",
                },
                json={
                    "@odata.id": (
                        f"{self.base_url}/directoryObjects/{user_id}"
                    )
                },
            )

            if response.status_code in (200, 204):
                audit_log(
                    action="ADD",
                    user_dn=upn,
                    group_dn=group_name,
                    success=True,
                )
                logger.debug(
                    "EntraID user added to group | upn=%s | group=%s",
                    upn,
                    group_name,
                )
            else:
                failed = True
                audit_log(
                    action="ADD",
                    user_dn=upn,
                    group_dn=group_name,
                    success=False,
                    details=response.text,
                )
                logger.error(
                    "Failed to add EntraID user | upn=%s | group=%s | result=%s",
                    upn,
                    group_name,
                    response.text,
                )

        return not failed

    def remove_members_from_group(
        self,
        group_name: str,
        upns: list[str],
    ) -> bool:
        if not upns:
            logger.info(
                "No users to remove | group=%s",
                group_name,
            )
            return True

        group_id = self.get_group_id(group_name)
        failed = False

        for upn in upns:
            user_id = self.find_user_id_by_upn(upn)

            if not user_id:
                failed = True
                continue

            response = requests.delete(
                f"{self.base_url}/groups/{group_id}/members/{user_id}/$ref",
                headers=self._get_headers(),
            )

            if response.status_code in (200, 204):
                audit_log(
                    action="REMOVE",
                    user_dn=upn,
                    group_dn=group_name,
                    success=True,
                )
                logger.debug(
                    "EntraID user removed from group | upn=%s | group=%s",
                    upn,
                    group_name,
                )
            else:
                failed = True
                audit_log(
                    action="REMOVE",
                    user_dn=upn,
                    group_dn=group_name,
                    success=False,
                    details=response.text,
                )
                logger.error(
                    "Failed to remove EntraID user | upn=%s | group=%s | result=%s",
                    upn,
                    group_name,
                    response.text,
                )

        return not failed

    