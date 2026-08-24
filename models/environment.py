from dataclasses import dataclass
from typing import Optional


@dataclass
class Environment:

    name: str
    display_name: str
    env_type: str

    enabled: bool = True

    host: Optional[str] = None
    port: Optional[int] = None
    use_ssl: bool = True

    search_base: Optional[str] = None

    tenant_id: Optional[str] = None
    client_id: Optional[str] = None

    secret_name: Optional[str] = None