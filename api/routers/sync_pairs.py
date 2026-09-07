import traceback

from fastapi import APIRouter, HTTPException

from api.schemas import SyncPairPayload
from models.sync_pair import SyncPair
from repositories.sync_pair_repository import SyncPairRepository

router = APIRouter(prefix="/api/sync-pairs", tags=["sync-pairs"])
repo = SyncPairRepository()


def _build_engine():
    """Instantiate a fresh SyncEngine reading current config (deferred imports)."""
    from repositories.directory_repository import DirectoryRepository
    from services.service_factory import ServiceFactory
    from services.sync_engine import SyncEngine
    from services.sync_service import SyncService

    dir_repo = DirectoryRepository()
    dirs = {d.name: d for d in dir_repo.get_all()}

    factory = ServiceFactory()

    ldap_dir = (
        next((d for d in dirs.values() if d.dir_type == "AD"), None)
        or next((d for d in dirs.values() if d.dir_type == "LDAP"), None)
    )
    entra_dir = next((d for d in dirs.values() if d.dir_type == "ENTRA"), None)
    evq_dir   = next((d for d in dirs.values() if d.dir_type == "LDS"), None)

    ldap_svc  = factory.get(ldap_dir.name)  if ldap_dir  else None
    entra_svc = factory.get(entra_dir.name) if entra_dir else None
    evq_svc   = factory.get(evq_dir.name)   if evq_dir   else None

    sync_svc = SyncService(
        ldap_service=ldap_svc,
        entraid_service=entra_svc,
        evq_service=evq_svc,
    )
    # Pass factory so SyncEngine can resolve any directory for change detection
    return SyncEngine(sync_svc, factory=factory)



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
