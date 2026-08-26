from services.sync_engine import SyncEngine
from services.sync_service import SyncService
from services.service_factory import ServiceFactory


services = ServiceFactory()
ldap = services.get("AD_DF2")
entra = services.get("ENTRA_DF2")
evq = services.get("LDS_TEST")

sync_service = SyncService(
    ldap_service=ldap,
    entraid_service=entra,
    evq_service=evq
)

engine = SyncEngine(sync_service)

engine.run()