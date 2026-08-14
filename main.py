from services.ldap_service import LDAPService
from utils.logging_config import logger
from utils.audit import audit_log
import importlib

ldap = LDAPService()

def print_group_members():
    print("Which group do you want to see?")
    print("1) Python-Test-Group-1 (On-Premise)")
    print("2) Python-Test-Group-2 (On-Premise)")
    option = input("Select a group: ").strip()

    if option == "1":
        get_group_members("Python-Test-Group-1")
    elif option == "2":
        get_group_members("Python-Test-Group-2")
    

def get_group_members(group_name: str):
    members = ldap.get_group_members(group_name)
    if not members:
        print(f"No members found for group '{group_name}'.")
        return

    for member in members:
        print(member)

def add_user_to_group(group_name: str, email: str):
    user_dn = ldap.find_user_by_email(email)
    group_dn = ldap.get_group_dn(group_name)
    ldap.add_members_to_group(group_dn, [user_dn])

def remove_user_from_group(group_name: str, email: str):
    user_dn = ldap.find_user_by_email(email)
    group_dn = ldap.get_group_dn(group_name)
    ldap.remove_members_from_group(group_dn, [user_dn])

def sync_groups(source_group: str, target_group: str):

    source_members = ldap.get_group_members(source_group)
    target_members = ldap.get_group_members(target_group)

    members_to_add = list(source_members - target_members)
    members_to_remove = list(target_members - source_members)

    target_dn = ldap.get_group_dn(target_group)
    ldap.add_members_to_group(target_dn, members_to_add)
    ldap.remove_members_from_group(target_dn, members_to_remove)

    audit_log(
        action="SYNC",
        user_dn=source_group,
        group_dn=target_group,
        success=True)

def main() -> None:

    while True:
        print()
        print("1) Run test file")
        print("2) Print group members")
        print("3) Sync on-premise groups (GRP1 -> GRP2)")
        print("4) Sync EntraID group with on-premise group (GRP3 -> GRP4)")
        print("0) Exit")
        option = input("Select an option: ").strip()

        if option == "1":
            test_file = input("Type the file's name: ").strip()
            try:
                module = importlib.import_module(f"tests.{test_file}")
                module.run()
            except ModuleNotFoundError:
                print(f"Test '{test_file}' not found.")
            except Exception as ex:
                print(f"Error running test: {ex}")

        elif option == "2":
            print_group_members()

        elif option == "3":
            sync_groups("Python-Test-Group-1", "Python-Test-Group-2")

        elif option == "0":
            break
        

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Unhandled application error")
        raise