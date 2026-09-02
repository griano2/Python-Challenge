from dataclasses import dataclass
from typing import Optional


@dataclass
class Environment:

    name: str
    env_type: str
    display_name: Optional[str] = None

    enabled: bool = True

    host: Optional[str] = None
    port: Optional[int] = None
    use_ssl: bool = True

    search_base: Optional[str] = None
    group_filter_attribute: Optional[str] = None
    member_attribute: Optional[str] = None
    user_id_attribute: Optional[str] = None
    uid_attribute: str = "uidNumber"
    group_name_is_alias: Optional[bool] = None

    tenant_id: Optional[str] = None
    client_id: Optional[str] = None
    authority: Optional[str] = None
    graph_base_url: Optional[str] = None
    scopes: Optional[list[str]] = None

    bind_username: Optional[str] = None
    secret_name: Optional[str] = None