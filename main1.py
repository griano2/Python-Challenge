import argparse

from models.sync_pair import SyncPair
from repositories.directory_repository import DirectoryRepository
from services.sync_engine import SyncEngine
from services.sync_service import SyncService
from services.service_factory import ServiceFactory


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run configured synchronization pairs."
    )
    parser.add_argument(
        "-t",
        "--task",
        nargs=4,
        metavar=("SOURCE_DIR", "SOURCE_GROUP", "TARGET_DIR", "TARGET_GROUP"),
        help="Run one pair: source directory/group followed by target directory/group.",
    )
    return parser.parse_args()


def get_direction(source_type: str, target_type: str) -> str:
    directions = {
        ("AD", "AD"): "AD_TO_AD",
        ("AD", "LDS"): "AD_TO_LDS",
        ("LDS", "AD"): "LDS_TO_AD",
        ("ENTRA", "AD"): "ENTRA_TO_AD",
        ("AD", "ENTRA"): "AD_TO_ENTRA",
    }
    try:
        return directions[(source_type, target_type)]
    except KeyError as error:
        raise ValueError(
            f"Unsupported synchronization direction: {source_type} -> {target_type}"
        ) from error


def create_task(values):
    source_directory, source_group, target_directory, target_group = values
    directory_repository = DirectoryRepository()
    source = directory_repository.get(source_directory)
    target = directory_repository.get(target_directory)

    if source is None:
        raise ValueError(f"Directory not found: {source_directory}")
    if target is None:
        raise ValueError(f"Directory not found: {target_directory}")

    return SyncPair(
        name=f"CLI sync: {source_group} -> {target_group}",
        source_directory=source_directory,
        source_group=source_group,
        target_directory=target_directory,
        target_group=target_group,
        direction=get_direction(source.dir_type, target.dir_type),
    )


def main():
    args = parse_args()
    services = ServiceFactory()
    ldap = services.get("AD_DF2")
    entra = services.get("ENTRA_DF2")
    evq = services.get("LDS_TEST")

    sync_service = SyncService(
        ldap_service=ldap,
        entraid_service=entra,
        evq_service=evq
    )

    engine = SyncEngine(sync_service, factory=services)

    if args.task:
        engine.run_pair(create_task(args.task))
    else:
        engine.run()


if __name__ == "__main__":
    main()