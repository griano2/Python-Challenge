from services.ldap_service import LDAPService
from services.entraid_service import EntraIDService
from services.envq_service import EVQLDAPService
from utils.logging_config import logger
from utils.audit import audit_log
import importlib, re

ldap = LDAPService()
entra = EntraIDService(client_id="14d82eec-204b-4c2f-b7e8-296a70dab67e")
evq = EVQLDAPService()

def print_group_members():
    print("Which group do you want to see?")
    print("1) Python-Test-Group-1 (On-Premise)")
    print("2) Python-Test-Group-2 (On-Premise)")
    print("3) Python-Test-Group-4 (On-Premise)")
    print("4) Python-Test-Group-5 (On-Premise)")
    print("5) Other_testing-ldap-grpter (LDS ENVQ)")
    option = input("Select a group: ").strip()

    if option == "1":
        get_group_members("Python-Test-Group-1")
    elif option == "2":
        get_group_members("Python-Test-Group-2")
    elif option == "3":
        get_group_members("Python-Test-Group-4")
    elif option == "4":
        get_group_members("Python-Test-Group-5") 
    elif option == "5":
        members = evq.get_group_members("Other_testing-ldap-grpter")

        for member in sorted(members):
            print(member)

def get_group_members(group_name: str):
    members = ldap.get_group_members(group_name)
    if not members:
        print(f"No members found for group '{group_name}'.")
        return

    for member in members:
        print(member)

def sync_ad_groups(source_group: str, target_group: str):

    source_members = ldap.get_group_members(source_group)
    target_members = ldap.get_group_members(target_group)

    members_to_add = list(source_members - target_members)
    members_to_remove = list(target_members - source_members)

    target_dn = ldap.get_group_dn(target_group)
    ldap.add_members_to_group(target_dn, members_to_add)
    ldap.remove_members_from_group(target_dn, members_to_remove)

    audit_log(
        action="SYNC_AD",
        user_dn=source_group,
        group_dn=target_group,
        success=True)

def sync_entraid_to_ad(source_group: str, target_group: str):

    cloud_upns = entra.get_group_members(source_group)

    source_dns = set()
    for upn in cloud_upns:
        dn = ldap.find_user_by_email(upn)
        if dn:
            source_dns.add(dn)
        else:
            logger.warning("No on-prem match for %s", upn)

    target_dns = ldap.get_group_members(target_group)

    members_to_add = list(source_dns - target_dns)
    members_to_remove = list(target_dns - source_dns)

    target_dn = ldap.get_group_dn(target_group)
    ldap.add_members_to_group(target_dn, members_to_add)
    ldap.remove_members_from_group(target_dn, members_to_remove)

    audit_log(
        action="SYNC_ENTRAID",
        user_dn=source_group,
        group_dn=target_group,
        success=True)

def sync_lds_to_ad(source_alias: str, target_group: str):
    source_members = evq.get_group_members(source_alias)
    target_dns = ldap.get_group_members(target_group)

    members_to_add = list(source_members - target_dns)
    members_to_remove = list(target_dns - source_members)

    target_dn = ldap.get_group_dn(target_group)
    ldap.add_members_to_group(target_dn, members_to_add)
    ldap.remove_members_from_group(target_dn, members_to_remove)

    print(f"Source members : {len(source_members)}")
    print(f"Target members : {len(target_dns)}")
    print(f"To add         : {len(members_to_add)}")
    print(f"To remove      : {len(members_to_remove)}")

def sync_ad_to_lds(source_group: str, target_alias: str):
    ad_members = ldap.get_group_members(source_group)
    lds_members = evq.get_group_members(target_alias)

    source_users = {}
    target_users = {}

    for ad_dn in ad_members:
        lds_entry = evq.find_lds_user_by_ad_dn(ad_dn)
        if not lds_entry:
            continue

        identity = get_identity(lds_entry.entry_dn)
        source_users[identity] = lds_entry.entry_dn

    for lds_dn in lds_members:
        identity = get_identity(lds_dn)
        target_users[identity] = lds_dn

    source_ids = set(source_users.keys())
    target_ids = set(target_users.keys())

    members_to_add = [
        source_users[user]
        for user in (source_ids - target_ids)
    ]

    members_to_remove = [
        target_users[user]
        for user in (target_ids - source_ids)
    ]

    evq.add_members_to_group(target_alias, members_to_add)

    print("Members to remove:")
    for dn in members_to_remove:
        print(dn)
    evq.remove_members_from_group(target_alias, members_to_remove)

    print(f"Source identities: {len(source_ids)}")
    print(f"Target identities: {len(target_ids)}")
    print(f"To add: {len(members_to_add)}")
    print(f"To remove: {len(members_to_remove)}")    

def get_identity(dn: str) -> str:
    match = re.search(r"CN=([^,]+)", dn, re.IGNORECASE)
    if not match:
        return ""
    return match.group(1).strip().upper()

def main() -> None:

    while True:
        print()
        print("1) Run test file")
        print("2) Print group members")
        print("3) Sync on-premise groups (GRP1 -> GRP2)")
        print("4) Sync EntraID group with on-premise group (GRP3 -> GRP4)")
        print("5) Sync LDS EVQ group with on-premise group (GRP6 -> GRP5)")
        print("6) Sync on-premise group with LDS EVQ group  (GRP5 -> GRP6)")
        print("7) Test fcn")
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
            sync_ad_groups("Python-Test-Group-1", "Python-Test-Group-2")

        elif option == "4":
            sync_entraid_to_ad("Python-Test-Group-3", "Python-Test-Group-4")

        elif option == "5":
            sync_lds_to_ad("Other_testing-ldap-grpter","Python-Test-Group-5")
            
        elif option == "6":
            sync_ad_to_lds("Python-Test-Group-5", "Other_testing-ldap-grpter")
        
        elif option == "7":
            print(evq.get_group_members("Other_testing-ldap-grpter"))

        elif option == "0":
            break
        

if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Unhandled application error")
        raise