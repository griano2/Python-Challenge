from fastapi import APIRouter, HTTPException

from api.schemas import EnvironmentPayload
from models.environment import Environment
from repositories.environment_repository import EnvironmentRepository

router = APIRouter(prefix="/api/environments", tags=["environments"])
repo = EnvironmentRepository()


@router.get("")
def list_environments():
    return [vars(e) for e in repo.get_all()]


@router.post("", status_code=201)
def create_environment(payload: EnvironmentPayload):
    env = Environment(**payload.model_dump())
    try:
        repo.create(env)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return vars(env)


@router.put("/{name}")
def update_environment(name: str, payload: EnvironmentPayload):
    env = Environment(**payload.model_dump())
    try:
        repo.update(name, env)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return vars(env)


@router.delete("/{name}", status_code=204)
def delete_environment(name: str):
    try:
        repo.delete(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
