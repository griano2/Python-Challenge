from services.entraid_service import EntraIDService

GROUP_NAME = "Python-Test-Group-3"
CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"

UPNS = [
    "AAlhashous@slb-tst.com",
    "NMajid5@slb-tst.com",
    "AIgoshkin@slb-tst.com",
    "AAzmir2@slb-tst.com",
]


def run() -> None:
    entra = EntraIDService(client_id=CLIENT_ID)

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
