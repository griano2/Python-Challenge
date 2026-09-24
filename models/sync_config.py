from dataclasses import dataclass, field

from models.sync_pair import SyncPair


@dataclass
class GroupMapping:
    source_group: str
    target_group: str
    enabled: bool = True


@dataclass
class SyncConfig:
    name: str
    direction: str

    source_directory: str
    target_directory: str

    enabled: bool = True
    mappings: list[GroupMapping] = field(default_factory=list)


def expand_to_pairs(config: SyncConfig) -> list[SyncPair]:
    """Turn each enabled mapping of an enabled config into a runnable SyncPair."""
    return [
        SyncPair(
            name=f"{config.name}::{m.source_group}->{m.target_group}",
            source_directory=config.source_directory,
            source_group=m.source_group,
            target_directory=config.target_directory,
            target_group=m.target_group,
            direction=config.direction,
            enabled=True,
        )
        for m in config.mappings
        if m.enabled
    ]
