from services.sync_engine import SyncEngine
from services.sync_service import SyncService
from services.entraid_service import EntraIDService
from services.service_factory import ServiceFactory


services = ServiceFactory()
ldap = services.get("AD_DF2")
entra = EntraIDService(client_id="14d82eec-204b-4c2f-b7e8-296a70dab67e")
evq = services.get("LDS_TEST")

sync_service = SyncService(
    ldap_service=ldap,
    entraid_service=entra,
    evq_service=evq
)

engine = SyncEngine(sync_service)

engine.run()