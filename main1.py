from services.sync_engine import SyncEngine
from services.sync_service import SyncService
from services.ldap_service import LDAPService
from services.entraid_service import EntraIDService


ldap = LDAPService()
entra = EntraIDService(client_id="14d82eec-204b-4c2f-b7e8-296a70dab67e")
evq = LDAPService(
    host="evq.lds.slb.com",
    directory_type="LDS",
)

sync_service = SyncService(
    ldap_service=ldap,
    entraid_service=entra,
    evq_service=evq
)

engine = SyncEngine(sync_service)

engine.run()