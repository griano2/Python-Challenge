import traceback

from fastapi import APIRouter, HTTPException

from api.schemas import SyncPairPayload
from models.sync_pair import SyncPair
from repositories.sync_pair_repository import SyncPairRepository

router = APIRouter(prefix="/api/sync-pairs", tags=["sync-pairs"])
repo = SyncPairRepository()


def _build_engine():
    """Instantiate a fresh SyncEngine reading current config (deferred imports)."""
    from repositories.environment_repository import EnvironmentRepository
    from services.service_factory import ServiceFactory
    from services.sync_engine import SyncEngine
    from services.sync_service import SyncService

    env_repo = EnvironmentRepository()
    envs = {e.name: e for e in env_repo.get_all()}

    factory = ServiceFactory()

    ldap_env  = next((e for e in envs.values() if e.env_type in {"AD", "LDS", "LDAP"}), None)
    entra_env = next((e for e in envs.values() if e.env_type == "ENTRA"), None)
    evq_env   = next((e for e in envs.values() if e.env_type == "LDS"), None)

    ldap_svc  = factory.get(ldap_env.name)  if ldap_env  else None
    entra_svc = factory.get(entra_env.name) if entra_env else None
    evq_svc   = factory.get(evq_env.name)   if evq_env   else None

    sync_svc = SyncService(
        ldap_service=ldap_svc,
        entraid_service=entra_svc,
        evq_service=evq_svc,
    )
    return SyncEngine(sync_svc)


@router.get("")
def list_sync_pairs():
    from dataclasses import asdict
    return [asdict(p) for p in repo.get_all()]


@router.post("", status_code=201)
def create_sync_pair(payload: SyncPairPayload):
    pair = SyncPair(**payload.model_dump())
    try:
        repo.create(pair)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    from dataclasses import asdict
    return asdict(pair)


@router.put("/{name}")
def update_sync_pair(name: str, payload: SyncPairPayload):
    pair = SyncPair(**payload.model_dump())
    try:
        repo.update(name, pair)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    from dataclasses import asdict
    return asdict(pair)


@router.delete("/{name}", status_code=204)
def delete_sync_pair(name: str):
    try:
        repo.delete(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{name}/run")
def run_sync_pair(name: str):
    pair = repo.get_by_name(name)
    if not pair:
        raise HTTPException(status_code=404, detail=f"Sync pair not found: {name}")

    try:
        engine = _build_engine()
        engine.run_pair(pair)
        return {"status": "success", "pair": name}
    except Exception as e:
        error_detail = traceback.format_exc()
        return {"status": "error", "pair": name, "detail": str(e), "traceback": error_detail}


@router.post("/run-enabled")
def run_all_enabled():
    pairs = repo.get_enabled()
    results = []
    engine = None

    try:
        engine = _build_engine()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize engine: {str(e)}")

    for pair in pairs:
        try:
            engine.run_pair(pair)
            results.append({"pair": pair.name, "status": "success"})
        except Exception as e:
            results.append({"pair": pair.name, "status": "error", "detail": str(e)})

    return {"results": results}
