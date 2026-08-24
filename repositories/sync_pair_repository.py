import json

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

    def get_by_name(self, name: str) -> SyncPair | None:
        for pair in self.get_all():
            if pair.name == name:
                return pair
        return None