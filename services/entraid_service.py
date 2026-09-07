import os
from pathlib import Path
from typing import Optional
import msal
import requests
from datetime import datetime, timezone, timedelta
from utils.audit import audit_log
from utils.logging_config import logger

CACHE_DIR = Path(__file__).parent.parent / "config"
CACHE_FILE = CACHE_DIR / ".entra_token_cache.bin"


class EntraIDService:

    def __init__(
        self,
        client_id: str,
        tenant_id: str,
        authority: str,
        graph_base_url: str,
        scopes: list[str],
        secret_name: Optional[str] = None,
    ):
        if not authority:
            raise ValueError("Entra directory requires authority")
        if not graph_base_url:
            raise ValueError("Entra directory requires graph_base_url")

        # Filtrar o normalizar scopes para permisos delegados interactivos
        delegated_scopes = [s for s in (scopes or []) if not s.endswith("/.default")]
        if not delegated_scopes:
            delegated_scopes = [
                "Group.ReadWrite.All",
                "User.Read",
            ]

        self.token_cache = msal.SerializableTokenCache()
        if CACHE_FILE.exists():
            try:
                self.token_cache.deserialize(CACHE_FILE.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("No se pudo cargar la caché de tokens de Entra: %s", e)

        self.app = msal.PublicClientApplication(
            client_id=client_id,
            authority=authority,
            token_cache=self.token_cache,
        )

        self.base_url = graph_base_url.rstrip("/")
        self.scopes = delegated_scopes

        logger.info(
            "EntraIDService initialized (Interactive / Delegated) | tenant=%s",
            tenant_id
        )

    def _save_cache(self) -> None:
        if self.token_cache.has_state_changed:
            try:
                CACHE_FILE.write_text(self.token_cache.serialize(), encoding="utf-8")
            except Exception as e:
                logger.warning("No se pudo guardar la caché de tokens de Entra: %s", e)

    def _get_token(self) -> str:
        # 1. Intentar obtención silenciosa desde la caché
        accounts = self.app.get_accounts()
        if accounts:
            logger.debug("Intentando obtención silenciosa de token para %s", accounts[0].get("username"))
            result = self.app.acquire_token_silent(
                scopes=self.scopes,
                account=accounts[0],
            )
            if result and "access_token" in result:
                self._save_cache()
                return result["access_token"]

        # 2. Flujo interactivo: abre el navegador con la pantalla oficial de Microsoft
        logger.info("Abriendo ventana de navegador para inicio de sesión en Microsoft...")
        print("\n" + "=" * 70)
        print(">>> INICIANDO SESIÓN EN MICROSOFT: Por favor completa el login en la")
        print(">>> ventana del navegador que se acaba de abrir.")
        print("=" * 70 + "\n")

        result = self.app.acquire_token_interactive(
            scopes=self.scopes,
            prompt="select_account",
        )

        if "access_token" not in result:
            logger.error(
                "Error en autenticación interactiva de Entra ID | detalles=%s",
                result.get("error_description")
            )
            raise Exception(
                f"Error al autenticar con Microsoft: {result.get('error_description')}"
            )

        self._save_cache()
        logger.info("Autenticación con Microsoft exitosa")
        return result["access_token"]

    def _get_headers(self) -> dict:

        return {
            "Authorization": f"Bearer {self._get_token()}"
        }

    def _raise_for_graph_response(self, response) -> None:
        if response.status_code in (401, 403):
            raise PermissionError(
                f"Microsoft Graph rechazó la solicitud con HTTP {response.status_code}. "
                f"Detalle: {response.text}"
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
    
