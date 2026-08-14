from pydantic import BaseModel, EmailStr

class UserGroupRequest(BaseModel):
    email: EmailStr
    group_name: str


class SyncRequest(BaseModel):
    source_group: str
    target_group: str