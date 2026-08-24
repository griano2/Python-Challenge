from dataclasses import dataclass


@dataclass
class SyncPair:
    name: str

    source_environment: str
    source_group: str

    target_environment: str
    target_group: str

    direction: str
    enabled: bool = True