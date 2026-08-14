from fastapi import FastAPI, Depends, HTTPException
from services.ldap_service import LDAPService
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="LDAP Group Management API",
    description="Manage LDAP group memberships",
    version="1.0.0"
)

ldap = LDAPService()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def root():
    return {
        "message": "LDAP Group Management API"
    }

@app.get("/groups/{group_name}/members")
def get_group_members(group_name: str):

    members = ldap.get_group_members(group_name)
    return {
        "group": group_name,
        "member_count": len(members),
        "members": list(members)
    }

@app.post("/groups/{group_name}/users/{email}")
def add_user_to_group(group_name: str, email: str):

    user_dn = ldap.find_user_by_email(email)
    if not user_dn:
        raise HTTPException(status_code=404, detail=f"User '{email}' not found")

    group_dn = ldap.get_group_dn(group_name)
    if not group_dn:
        raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found")

    ldap.add_members_to_group(group_dn, [user_dn])
    return {
        "message": "User added successfully",
        "email": email,
        "group": group_name
    }

@app.delete("/groups/{group_name}/users/{email}")
def remove_user_from_group(group_name: str, email: str):

    user_dn = ldap.find_user_by_email(email)
    if not user_dn:
        raise HTTPException(status_code=404, detail=f"User '{email}' not found")

    group_dn = ldap.get_group_dn(group_name)
    if not group_dn:
        raise HTTPException(status_code=404, detail=f"Group '{group_name}' not found")

    ldap.remove_members_from_group(group_dn, [user_dn])
    return {
        "message": "User removed successfully",
        "email": email,
        "group": group_name
    }

@app.post("/groups/sync")
def sync_groups(source_group: str, target_group: str):

    source_members = ldap.get_group_members(source_group)
    target_members = ldap.get_group_members(target_group)

    members_to_add = list(source_members - target_members)
    members_to_remove = list(target_members - source_members)

    target_dn = ldap.get_group_dn(target_group)
    if not target_dn:
        raise HTTPException(status_code=404, detail=f"Group '{target_group}' not found")
    
    ldap.add_members_to_group(target_dn, members_to_add)
    ldap.remove_members_from_group(target_dn, members_to_remove)

    return {
        "source_group": source_group,
        "target_group": target_group,
        "added": len(members_to_add),
        "removed": len(members_to_remove)
    }