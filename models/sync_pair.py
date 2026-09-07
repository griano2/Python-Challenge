from dataclasses import dataclass


@dataclass
class SyncPair:
    name: str

    source_directory: str
    source_group: str

    target_directory: str
    target_group: str

    direction: str
    enabled: bool = True