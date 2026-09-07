import json
from dataclasses import asdict
from typing import Optional

from models.sync_pair import SyncPair


class SyncPairRepository:

    def __init__(self, config_file="config/sync_pairs.json"):
        self.config_file = config_file

    def get_all(self) -> list[SyncPair]:
        with open(self.config_file, "r", encoding="utf-8") as file:
            data = json.load(file)
        return [SyncPair(**item) for item in data]

    def get_enabled(self) -> list:
        return [pair for pair in self.get_all() if pair.enabled]

    def get_by_name(self, name: str) -> Optional[SyncPair]:
        for pair in self.get_all():
            if pair.name == name:
                return pair
        return None

    def save_all(self, pairs: list[SyncPair]) -> None:
        data = [asdict(p) for p in pairs]
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    def create(self, pair: SyncPair) -> SyncPair:
        pairs = self.get_all()
        if any(p.name == pair.name for p in pairs):
            raise ValueError(f"Sync pair already exists: {pair.name}")
        pairs.append(pair)
        self.save_all(pairs)
        return pair

    def update(self, name: str, pair: SyncPair) -> SyncPair:
        pairs = self.get_all()
        for i, p in enumerate(pairs):
            if p.name == name:
                pairs[i] = pair
                self.save_all(pairs)
                return pair
        raise ValueError(f"Sync pair not found: {name}")

    def delete(self, name: str) -> None:
        pairs = self.get_all()
        filtered = [p for p in pairs if p.name != name]
        if len(filtered) == len(pairs):
            raise ValueError(f"Sync pair not found: {name}")
        self.save_all(filtered)