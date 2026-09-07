import msal
import requests
from services.vault_service import VaultService
from datetime import datetime, timezone, timedelta
from utils.audit import audit_log
from utils.logging_config import logger


class EntraIDService:

    def __init__(
        self,
        client_id: str,
        tenant_id: str,
        authority: str,
        graph_base_url: str,
        scopes: list[str],
        secret_name: str,
    ):
        if not authority:
            raise ValueError("Entra directory requires authority")
        if not graph_base_url:
            raise ValueError("Entra directory requires graph_base_url")
        if not scopes:
            raise ValueError("Entra directory requires scopes")
        if not secret_name:
            raise ValueError("Entra directory requires secret_name")

        client_secret = VaultService().get_secret(secret_name)

        self.app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=authority,
        )

        self.base_url = graph_base_url.rstrip("/")
        self.scopes = scopes

        logger.info(
            "EntraIDService initialized | tenant=%s",
            tenant_id
        )

    def _get_token(self) -> str:

        logger.debug("Requesting EntraID application token")

        result = self.app.acquire_token_for_client(
            scopes=self.scopes,
        )

        if "access_token" not in result:

            logger.error(
                "EntraID application authentication failed | details=%s",
                result.get("error_description")
            )

            raise Exception(
                f"Application auth failed: "
                f"{result.get('error_description')}"
            )

        logger.info(
            "EntraID application authentication successful"
        )

        return result["access_token"]

    def _get_headers(self) -> dict:

        return {
            "Authorization": f"Bearer {self._get_token()}"
        }

    def _raise_for_graph_response(self, response) -> None:
        if response.status_code in (401, 403):
            raise PermissionError(
                "Microsoft Graph rejected the application token with "
                f"HTTP {response.status_code}. Grant the app the application "
                "permissions Group.Read.All and GroupMember.Read.All, "
                "then grant admin consent. Add GroupMember.ReadWrite.All "
                "for membership changes."
            )

        response.raise_for_status()

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

        self._raise_for_graph_response(resp)

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

            self._raise_for_graph_response(resp)

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

        self._raise_for_graph_response(response)
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

    def get_group_modified_time(self, group_name: str) -> datetime | None:
        """Return the UTC datetime of the last modification of a group in Entra ID.

        Queries ``lastModifiedDateTime`` via the Graph API.
        Returns ``None`` if the group is not found or the call fails,
        so the caller defaults to running the sync.
        """
        try:
            params = {
                "$filter": f"displayName eq '{group_name}'",
                "$select": "id,displayName,lastModifiedDateTime",
            }

            resp = requests.get(
                f"{self.base_url}/groups",
                headers=self._get_headers(),
                params=params,
            )
            self._raise_for_graph_response(resp)

            groups = resp.json().get("value", [])

            if not groups:
                logger.warning(
                    "get_group_modified_time: group not found | group=%s",
                    group_name,
                )
                return None

            raw_ts = groups[0].get("lastModifiedDateTime")

            if not raw_ts:
                return None

            # Graph API returns ISO 8601: "2026-09-07T13:30:00Z"
            dt = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            return dt

        except Exception:
            logger.warning(
                "get_group_modified_time: could not retrieve lastModifiedDateTime | group=%s",
                group_name,
                exc_info=True,
            )
            return None
    
