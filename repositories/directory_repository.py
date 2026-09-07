import json
from dataclasses import asdict
from typing import Optional

from models.directory import Directory


class DirectoryRepository:

    def __init__(self, config_file="config/directories.json"):
        self.config_file = config_file

    def get_all(self) -> list[Directory]:
        with open(self.config_file, "r") as f:
            data = json.load(f)
        return [Directory(**item) for item in data]

    def get(self, name: str) -> Optional[Directory]:
        for d in self.get_all():
            if d.name == name:
                return d
        return None

    def save_all(self, directories: list[Directory]) -> None:
        data = []
        for d in directories:
            item = asdict(d)
            # Remove None values to keep JSON clean
            item = {k: v for k, v in item.items() if v is not None}
            data.append(item)
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def create(self, directory: Directory) -> Directory:
        dirs = self.get_all()
        if any(d.name == directory.name for d in dirs):
            raise ValueError(f"Directory already exists: {directory.name}")
        dirs.append(directory)
        self.save_all(dirs)
        return directory

    def update(self, name: str, directory: Directory) -> Directory:
        dirs = self.get_all()
        for i, d in enumerate(dirs):
            if d.name == name:
                dirs[i] = directory
                self.save_all(dirs)
                return directory
        raise ValueError(f"Directory not found: {name}")

    def delete(self, name: str) -> None:
        dirs = self.get_all()
        filtered = [d for d in dirs if d.name != name]
        if len(filtered) == len(dirs):
            raise ValueError(f"Directory not found: {name}")
        self.save_all(filtered)
