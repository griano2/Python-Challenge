import os
from pathlib import Path
from fastapi import APIRouter, HTTPException

from repositories.directory_repository import DirectoryRepository
from services.entraid_service import EntraIDService, CACHE_FILE

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _get_entra_service() -> EntraIDService:
    repo = DirectoryRepository()
    entra_dir = next((d for d in repo.get_all() if d.dir_type == "ENTRA"), None)
    if not entra_dir:
        raise HTTPException(
            status_code=404,
            detail="No se encontró un directorio configurado de tipo ENTRA",
        )

    return EntraIDService(
        client_id=entra_dir.client_id,
        tenant_id=entra_dir.tenant_id,
        authority=entra_dir.authority,
        graph_base_url=entra_dir.graph_base_url,
        scopes=entra_dir.scopes,
        secret_name=entra_dir.secret_name,
    )


@router.get("/status")
def auth_status():
    """Retorna el estado de autenticación actual del usuario con Microsoft Entra ID."""
    try:
        entra = _get_entra_service()
    except HTTPException:
        # Si no hay directorio Entra configurado, no bloqueamos el acceso
        return {"authenticated": True, "user": {"name": "Admin Local", "username": "local"}}

    accounts = entra.app.get_accounts()
    if not accounts:
        return {"authenticated": False, "user": None}

    # Intentar validación silenciosa
    token = entra.app.acquire_token_silent(scopes=entra.scopes, account=accounts[0])
    if token and "access_token" in token:
        entra._save_cache()
        acc = accounts[0]
        return {
            "authenticated": True,
            "user": {
                "name": acc.get("name") or acc.get("username"),
                "username": acc.get("username"),
            },
        }

    return {"authenticated": False, "user": None}


@router.post("/login")
def login():
    """Inicia el flujo interactivo de Microsoft abriendo la ventana oficial de login."""
    entra = _get_entra_service()
    try:
        # _get_token() dispara acquire_token_interactive si no hay token silencioso válido
        token = entra._get_token()
        accounts = entra.app.get_accounts()
        acc = accounts[0] if accounts else {}
        return {
            "status": "success",
            "user": {
                "name": acc.get("name") or acc.get("username"),
                "username": acc.get("username"),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
def logout():
    """Cierra la sesión activa eliminando las cuentas de la caché local."""
    try:
        entra = _get_entra_service()
        for account in entra.app.get_accounts():
            entra.app.remove_account(account)
        entra._save_cache()
    except Exception:
        pass

    if CACHE_FILE.exists():
        try:
            os.remove(CACHE_FILE)
        except OSError:
            pass

    return {"status": "success"}
