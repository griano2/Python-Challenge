from repositories.directory_repository import DirectoryRepository
from services.ldap_service import LDAPService
from services.entraid_service import EntraIDService

class ServiceFactory:

    def __init__(self):
        self.directory_repository = DirectoryRepository()
        self._services = {}

    def get(self, directory_name: str):
        if directory_name in self._services:
            return self._services[directory_name]
        directory = self.directory_repository.get(directory_name)

        if not directory:
            raise ValueError(f"Directory not found: {directory_name}")

        service = self._create_service(directory)
        self._services[directory_name] = service
        return service

    def _create_service(self, directory):
        if directory.dir_type in {"AD", "LDS", "LDAP"}:
            return LDAPService(
                host=directory.host,
                port=directory.port,
                use_ssl=directory.use_ssl,
                search_base=directory.search_base,
                group_filter_attribute=directory.group_filter_attribute,
                member_attribute=directory.member_attribute,
                user_id_attribute=directory.user_id_attribute,
                uid_attribute=directory.uid_attribute,
                group_name_is_alias=directory.group_name_is_alias,
                bind_username=directory.bind_username,
                secret_name=directory.secret_name,
            )

        elif directory.dir_type == "ENTRA":

            return EntraIDService(
                tenant_id=directory.tenant_id,
                client_id=directory.client_id,
                authority=directory.authority,
                graph_base_url=directory.graph_base_url,
                scopes=directory.scopes,
                secret_name=directory.secret_name,
            )

        raise ValueError(
            f"Unsupported directory type: "
            f"{directory.dir_type}"
        )