from repositories.environment_repository import EnvironmentRepository
from services.ldap_service import LDAPService
from services.entraid_service import EntraIDService

class ServiceFactory:

    def __init__(self):
        self.environment_repository = EnvironmentRepository()
        self._services = {}

    def get(self, environment_name: str):
        if environment_name in self._services:
            return self._services[environment_name]
        environment = self.environment_repository.get(environment_name)

        if not environment:
            raise ValueError(f"Environment not found: {environment_name}")

        service = self._create_service(environment)
        self._services[environment_name] = service
        return service

    def _create_service(self, environment):
        if environment.env_type in {"AD", "LDS", "LDAP"}:
            return LDAPService(
                host=environment.host,
                port=environment.port,
                use_ssl=environment.use_ssl,
                search_base=environment.search_base,
                group_filter_attribute=environment.group_filter_attribute,
                member_attribute=environment.member_attribute,
                user_id_attribute=environment.user_id_attribute,
                uid_attribute=environment.uid_attribute,
                group_name_is_alias=environment.group_name_is_alias,
                secret_name=environment.secret_name,
            )

        elif environment.env_type == "ENTRA":

            return EntraIDService(
                tenant_id=environment.tenant_id,
                client_id=environment.client_id,
                authority=environment.authority,
                graph_base_url=environment.graph_base_url,
                scopes=environment.scopes,
            )

        raise ValueError(
            f"Unsupported environment type: "
            f"{environment.env_type}"
        )