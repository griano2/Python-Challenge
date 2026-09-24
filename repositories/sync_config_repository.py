import json
from dataclasses import asdict
from typing import Optional

from models.sync_config import GroupMapping, SyncConfig


class SyncConfigRepository:

    def __init__(self, config_file="config/sync_configs.json"):
        self.config_file = config_file

    def _from_dict(self, item: dict) -> SyncConfig:
        mappings = [GroupMapping(**m) for m in item.get("mappings", [])]
        return SyncConfig(**{**item, "mappings": mappings})

    def get_all(self) -> list[SyncConfig]:
        with open(self.config_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        return [self._from_dict(item) for item in data]

    def get_enabled(self) -> list[SyncConfig]:
        return [config for config in self.get_all() if config.enabled]

    def get_by_name(self, name: str) -> Optional[SyncConfig]:
        for config in self.get_all():
            if config.name == name:
                return config
        return None

    def save_all(self, configs: list[SyncConfig]) -> None:
        data = [asdict(c) for c in configs]
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def create(self, config: SyncConfig) -> SyncConfig:
        configs = self.get_all()
        if any(c.name == config.name for c in configs):
            raise ValueError(f"Sync config already exists: {config.name}")
        configs.append(config)
        self.save_all(configs)
        return config

    def update(self, name: str, config: SyncConfig) -> SyncConfig:
        configs = self.get_all()
        for i, c in enumerate(configs):
            if c.name == name:
                configs[i] = config
                self.save_all(configs)
                return config
        raise ValueError(f"Sync config not found: {name}")

    def delete(self, name: str) -> None:
        configs = self.get_all()
        filtered = [c for c in configs if c.name != name]
        if len(filtered) == len(configs):
            raise ValueError(f"Sync config not found: {name}")
        self.save_all(filtered)
