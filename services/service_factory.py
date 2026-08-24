from repositories.environment_repository import EnvironmentRepository
from services.ldap_service import LDAPService
from services.evq_service import EVQLDAPService
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
        if environment.env_type == "AD":
            return LDAPService(
                host=environment.host,
                port=environment.port,
                use_ssl=environment.use_ssl
            )

        elif environment.env_type == "LDS":

            return EVQLDAPService(
                host=environment.host,
                port=environment.port,
                use_ssl=environment.use_ssl
            )

        elif environment.env_type == "ENTRA":

            return EntraIDService(
                tenant_id=environment.tenant_id,
                client_id=environment.client_id
            )

        raise ValueError(
            f"Unsupported environment type: "
            f"{environment.env_type}"
        )