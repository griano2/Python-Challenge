import os
import base64

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from utils.logging_config import logger


class VaultService:

    def __init__(self):
        vault_url = os.getenv("KEY_VAULT_URL")

        if not vault_url:
            raise ValueError("KEY_VAULT_URL is not configured")

        self.client = SecretClient(
            vault_url=vault_url,
            credential=DefaultAzureCredential()
        )

    def get_secret(self, secret_name: str) -> str:
        """
        Returns a decoded secret value from Azure Key Vault.
        Assumes secrets are stored Base64 encoded.
        """

        try:
            secret = self.client.get_secret(secret_name)

            value = base64.b64decode(
                secret.value.encode()
            ).decode()

            logger.info(
                "Secret '%s' retrieved successfully",
                secret_name
            )

            return value

        except Exception as ex:
            logger.error(
                "Failed retrieving secret '%s': %s",
                secret_name,
                ex
            )
            raise