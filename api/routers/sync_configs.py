from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from api.schemas import SyncConfigPayload
from models.sync_config import GroupMapping, SyncConfig, expand_to_pairs
from repositories.sync_config_repository import SyncConfigRepository

router = APIRouter(prefix="/api/sync-configs", tags=["sync-configs"])
repo = SyncConfigRepository()


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


def _to_config(payload: SyncConfigPayload) -> SyncConfig:
    mappings = [
        GroupMapping(
            source_group=m.source_group,
            target_group=(m.target_group or m.source_group),
            enabled=m.enabled,
        )
        for m in payload.mappings
    ]
    return SyncConfig(
        name=payload.name,
        direction=payload.direction,
        source_directory=payload.source_directory,
        target_directory=payload.target_directory,
        enabled=payload.enabled,
        mappings=mappings,
    )


def _run_config(config: SyncConfig, engine) -> dict:
    mapping_results = []
    for pair in expand_to_pairs(config):
        try:
            engine.run_pair(pair)
            mapping_results.append({
                "source_group": pair.source_group,
                "target_group": pair.target_group,
                "status": "success",
            })
        except Exception as e:
            mapping_results.append({
                "source_group": pair.source_group,
                "target_group": pair.target_group,
                "status": "error",
                "detail": str(e),
            })

    if not mapping_results:
        status = "skipped"
    elif all(m["status"] == "success" for m in mapping_results):
        status = "success"
    elif any(m["status"] == "success" for m in mapping_results):
        status = "partial"
    else:
        status = "error"

    return {"status": status, "config": config.name, "mappings": mapping_results}


@router.get("")
def list_sync_configs():
    return [asdict(c) for c in repo.get_all()]


@router.post("", status_code=201)
def create_sync_config(payload: SyncConfigPayload):
    config = _to_config(payload)
    try:
        repo.create(config)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return asdict(config)


@router.put("/{name}")
def update_sync_config(name: str, payload: SyncConfigPayload):
    config = _to_config(payload)
    try:
        repo.update(name, config)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return asdict(config)


@router.delete("/{name}", status_code=204)
def delete_sync_config(name: str):
    try:
        repo.delete(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{name}/run")
def run_sync_config(name: str):
    config = repo.get_by_name(name)
    if not config:
        raise HTTPException(status_code=404, detail=f"Sync config not found: {name}")

    try:
        engine = _build_engine()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to initialize engine: {str(e)}")

    return _run_config(config, engine)


@router.post("/run-enabled")
def run_all_enabled():
    configs = repo.get_enabled()
    results = []

    try:
        engine = _build_engine()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unable to initialize engine: {str(e)}")

    for config in configs:
        results.append(_run_config(config, engine))

    return {"results": results}
