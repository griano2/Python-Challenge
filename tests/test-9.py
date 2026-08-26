from services.service_factory import ServiceFactory

GROUP_NAME = "Python-Test-Group-3"
UPNS = [
    "AAlhashous@slb-tst.com",
    "NMajid5@slb-tst.com",
    "AIgoshkin@slb-tst.com",
    "AAzmir2@slb-tst.com",
]


def run() -> None:
    entra = ServiceFactory().get("ENTRA_DF2")

    succeeded = entra.add_members_to_group(
        GROUP_NAME,
        UPNS,
    )

    if succeeded:
        print(
            f"Added {len(UPNS)} users to {GROUP_NAME}."
        )
    else:
        print(
            f"Failed to add one or more users to {GROUP_NAME}."
        )


if __name__ == "__main__":
    run()
