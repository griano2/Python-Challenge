import msal
import requests
from utils.logging_config import logger


class EntraIDService:

    def __init__(self, client_id: str, tenant_id: str = "organizations"):
        self.app = msal.PublicClientApplication(
            client_id=client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
        )
        self.base_url = "https://graph.microsoft.com/v1.0"

    def _get_token(self) -> str:
        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(
                scopes=["Group.Read.All"],
                account=accounts[0],
            )
            if result and "access_token" in result:
                return result["access_token"]

        result = self.app.acquire_token_interactive(
            scopes=["Group.Read.All"],
        )
        if "access_token" not in result:
            raise Exception(f"Auth failed: {result.get('error_description')}")

        logger.info("EntraID auth successful")
        return result["access_token"]

    def _get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def get_group_id(self, group_name: str) -> str:
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
            logger.warning("EntraID group '%s' not found", group_name)
            raise Exception(f"Group '{group_name}' not found in EntraID")
        return groups[0]["id"]

    def get_group_members(self, group_name: str) -> set[str]:
        group_id = self.get_group_id(group_name)
        members = set()
        url = f"{self.base_url}/groups/{group_id}/members"

        while url:
            params = {"$select": "userPrincipalName", "$top": 999}
            resp = requests.get(url, headers=self._get_headers(), params=params)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("value", []):
                if item.get("userPrincipalName"):
                    members.add(item["userPrincipalName"])

            url = data.get("@odata.nextLink")

        logger.info("EntraID members | group=%s | count=%d", group_name, len(members))
        return members