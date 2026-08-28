import os, hvac
from utils.logging_config import logger

class VaultService:
    def get_client_secret(self, secret_path: str) -> str:
        _, client_secret = self.get_creds(secret_path)
        return client_secret

    def get_creds(self, secret_path: str) -> tuple[str, str]:
        token = os.getenv("rootToken")

        if token is None:
            logger.warning("Environment variable 'rootToken' is not set.")
            print("Warning: environment variable 'rootToken' is not set.")

        client = hvac.Client(url="http://127.0.0.1:8200", token=token)

        if not client.is_authenticated():
            logger.error("Vault authentication failed")
            raise Exception("Vault authentication failed")

        secret = client.secrets.kv.v2.read_secret_version(
            path=secret_path,
            mount_point="secret",
            raise_on_deleted_version=True)

        logger.info("Credentials successfully retrieved from Vault")

        return (secret["data"]["data"]["username"],
                secret["data"]["data"]["password"])

    def get_ad_creds(self) -> tuple[str, str]:

        token = os.getenv("rootToken")

        if token is None:
            logger.warning("Environment variable 'rootToken' is not set.")
            print("Warning: environment variable 'rootToken' is not set.")

        client = hvac.Client(url="http://127.0.0.1:8200", token=token)

        if not client.is_authenticated():
            logger.error("Vault authentication failed")
            raise Exception("Vault authentication failed")

        secret = client.secrets.kv.v2.read_secret_version(
            path="challenge/creds",
            mount_point="secret",
            raise_on_deleted_version=True)

        logger.info("Credentials successfully retrieved from Vault")

        return (secret["data"]["data"]["username"],
                secret["data"]["data"]["password"])

    def get_lds_creds(self) -> tuple[str, str]:
    
            token = os.getenv("rootToken")
    
            if token is None:
                logger.warning("Environment variable 'rootToken' is not set.")
                print("Warning: environment variable 'rootToken' is not set.")
    
            client = hvac.Client(url="http://127.0.0.1:8200", token=token)
    
            if not client.is_authenticated():
                logger.error("Vault authentication failed")
                raise Exception("Vault authentication failed")
    
            secret = client.secrets.kv.v2.read_secret_version(
                path="challenge/ldscreds",
                mount_point="secret",
                raise_on_deleted_version=True)
    
            logger.info("Credentials successfully retrieved from Vault")
    
            return (secret["data"]["data"]["username"],
                    secret["data"]["data"]["password"])