from fastapi import APIRouter, HTTPException

from api.schemas import DirectoryPayload
from models.directory import Directory
from repositories.directory_repository import DirectoryRepository

router = APIRouter(prefix="/api/directories", tags=["directories"])
repo = DirectoryRepository()


@router.get("")
def list_directories():
    return [vars(d) for d in repo.get_all()]


@router.post("", status_code=201)
def create_directory(payload: DirectoryPayload):
    directory = Directory(**payload.model_dump())
    try:
        repo.create(directory)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return vars(directory)


@router.put("/{name}")
def update_directory(name: str, payload: DirectoryPayload):
    directory = Directory(**payload.model_dump())
    try:
        repo.update(name, directory)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return vars(directory)


@router.delete("/{name}", status_code=204)
def delete_directory(name: str):
    try:
        repo.delete(name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
