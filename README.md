# Enterprise Directory Synchronization Engine

A robust, enterprise-grade identity and group synchronization platform built in Python. This framework provides seamless, bidirectional group membership synchronization across heterogeneous directory environments: **Active Directory (On-Premise LDAP)**, **Lightweight Directory Services (LDS / EVQ LDAP)**, and **Microsoft Entra ID (Cloud Azure AD via Microsoft Graph API)**, backed by **HashiCorp Vault** for secure credential management and structured audit logging.

---

## Table of Contents

- [1. System Architecture](#1-system-architecture)
  - [Architecture Overview](#architecture-overview)
  - [Design Patterns & Principles](#design-patterns--principles)
  - [Directory Synchronization Flow](#directory-synchronization-flow)
- [2. Service Profiles & Directory Connections](#2-service-profiles--directory-connections)
  - [Environment Configuration (`config/environments.json`)](#environment-configuration-configenvironmentsjson)
  - [Profile 1: Active Directory (`AD_DF2`)](#profile-1-active-directory-ad_df2)
  - [Profile 2: Lightweight Directory Services (`LDS_TEST`)](#profile-2-lightweight-directory-services-lds_test)
  - [Profile 3: Microsoft Entra ID (`ENTRA_DF2`)](#profile-3-microsoft-entra-id-entra_df2)
  - [Identity Attribute Mapping Matrix](#identity-attribute-mapping-matrix)
- [3. Secure Secrets Management](#3-secure-secrets-management)
  - [HashiCorp Vault Integration](#hashicorp-vault-integration)
  - [Vault Service Architecture](#vault-service-architecture)
  - [Security Principles](#security-principles)
- [4. Synchronization Pairs & Engine](#4-synchronization-pairs--engine)
  - [Sync Configuration (`config/sync_pairs.json`)](#sync-configuration-configsync_pairsjson)
  - [Configured Sync Pairs](#configured-sync-pairs)
  - [Delta Synchronization Algorithm](#delta-synchronization-algorithm)
- [5. Complete Script & Component Reference](#5-complete-script--component-reference)
  - [Entry Points & CLI](#entry-points--cli)
  - [Service Layer (`services/`)](#service-layer-services)
  - [Domain Models (`models/`)](#domain-models-models)
  - [Data Access Repositories (`repositories/`)](#data-access-repositories-repositories)
  - [Utilities & Observability (`utils/`)](#utilities--observability-utils)
  - [Test & Seeding Suite (`tests/`)](#test--seeding-suite-tests)
- [6. Audit Logging & Observability](#6-audit-logging--observability)
- [7. Installation & Setup Guide](#7-installation--setup-guide)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Vault Configuration](#vault-configuration)
  - [Usage Guide](#usage-guide)

---

## 1. System Architecture

### Architecture Overview

The system follows a clean, decoupled multi-tiered architecture separating configuration, data models, repository abstractions, identity connectors, business synchronization engines, and presentation/CLI interfaces.

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   CONFIGURATION LAYER                                   │
│   ┌─────────────────────────────────────────┐   ┌───────────────────────────────────┐   │
│   │         config/environments.json        │   │        config/sync_pairs.json     │   │
│   └────────────────────┬────────────────────┘   └─────────────────┬─────────────────┘   │
└────────────────────────┼──────────────────────────────────────────┼─────────────────────┘
                         │                                          │
                         ▼                                          ▼
┌─────────────────────────────────────────────┐   ┌───────────────────────────────────┐
│              DATA ACCESS LAYER              │   │         DATA ACCESS LAYER         │
│           EnvironmentRepository             │   │        SyncPairRepository         │
└────────────────────────┬────────────────────┘   └─────────────────┬─────────────────┘
                         │                                          │
                         ▼                                          │
┌─────────────────────────────────────────────┐                     │
│               SERVICE FACTORY               │◄──── [ VaultService (HashiCorp Vault) ]
│               ServiceFactory                │                     │
└────────────────────────┬────────────────────┘                     │
                         │                                          │
         ┌───────────────┼───────────────┐                          │
         ▼               ▼               ▼                          │
  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                   │
  │ LDAPService │ │ LDAPService │ │EntraIDServic│                   │
  │  (AD_DF2)   │ │ (LDS_TEST)  │ │ (ENTRA_DF2) │                   │
  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘                   │
         │               │               │                          │
         └───────────────┼───────────────┘                          │
                         ▼                                          ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                  SYNCHRONIZATION LAYER                                  │
│                 SyncService  ◄───────────────────────────  SyncEngine                   │
└────────────────────────┬────────────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
  ┌─────────────┐                 ┌─────────────┐
  │   main.py   │                 │  main1.py   │
  │ (CLI Menu)  │                 │(Batch Engine│
  └─────────────┘                 └─────────────┘
```

### Design Patterns & Principles

1. **Repository Pattern** ([`EnvironmentRepository`](repositories/environment_repository.py), [`SyncPairRepository`](repositories/sync_pair_repository.py)): Decouples JSON configuration storage from in-memory domain objects.
2. **Factory & Registry Pattern** ([`ServiceFactory`](services/service_factory.py)): Dynamically creates and caches directory connectors (`LDAPService` or `EntraIDService`) based on environment types and properties.
3. **Engine & Strategy Pattern** ([`SyncEngine`](services/sync_engine.py), [`SyncService`](services/sync_service.py)): Decouples sync orchestration and configuration loop from directory-specific translation strategies (`AD_TO_AD`, `ENTRA_TO_AD`, `AD_TO_ENTRA`, `AD_TO_LDS`, `LDS_TO_AD`).
4. **Zero-Hardcoded Secrets**: Credential management is delegated to HashiCorp Vault via [`VaultService`](services/vault_service.py).
5. **Idempotence & Delta Calculation**: Synchronization operations compute mathematical set differences (`Source \ Target` and `Target \ Source`) to issue minimal additive and subtractive changes.

### Directory Synchronization Flow

```text
 [CLI / main1.py]              [SyncService]              [Source Dir]         [Target Dir]         [Audit Log]
        │                            │                         │                    │                    │
   (1)  │── Execute Sync Pair ──────►│                         │                    │                    │
        │                            │── (2) Query Members ───►│                    │                    │
        │                            │◄── Return Identifiers ──┘                    │                    │
        │                            │                                              │                    │
        │                            │── (3) Query Members ────────────────────────►│                    │
        │                            │◄── Return Current Members ───────────────────┘                    │
        │                            │                                              │                    │
        │                            ├── (4) Correlate Identities across systems    │                    │
        │                            │       (UPN <-> DN <-> uidNumber / ID)        │                    │
        │                            │                                              │                    │
        │                            ├── (5) Compute Deltas:                        │                    │
        │                            │       Additions = Source - Target            │                    │
        │                            │       Removals  = Target - Source            │                    │
        │                            │                                              │                    │
        │                            │── (6) Apply Additions (MODIFY_ADD / POST) ──►│                    │
        │                            │── (7) Apply Removals (MODIFY_DELETE / DEL) ─►│                    │
        │                            │                                              │                    │
        │                            │── (8) Record Audit Event ────────────────────────────────────────►│
        │◄── Sync Completed ─────────│
```

---

## 2. Service Profiles & Directory Connections

All directory profiles are declared declaratively in [`config/environments.json`](config/environments.json) and parsed into strongly-typed [`Environment`](models/environment.py) dataclasses.

### Environment Configuration (`config/environments.json`)

```json
[
  {
    "name": "LDS_TEST",
    "env_type": "LDS",
    "host": "evq.lds.slb.com",
    "port": 636,
    "use_ssl": true,
    "search_base": "O=slb,C=an",
    "group_filter_attribute": "alias",
    "member_attribute": "uniqueMember",
    "user_id_attribute": "ID",
    "uid_attribute": "uidNumber",
    "group_name_is_alias": true,
    "secret_name": "challenge/ldscreds"
  },
  {
    "name": "AD_DF2",
    "env_type": "AD",
    "host": "dir-tst.slb-tst.com",
    "port": 636,
    "use_ssl": true,
    "search_base": "DC=dir-tst,DC=slb-tst,DC=com",
    "group_filter_attribute": "cn",
    "member_attribute": "member",
    "user_id_attribute": "ID",
    "uid_attribute": "uidNumber",
    "group_name_is_alias": false,
    "secret_name": "challenge/creds"
  },
  {
    "name": "ENTRA_DF2",
    "env_type": "ENTRA",
    "tenant_id": "organizations",
    "client_id": "14d82eec-204b-4c2f-b7e8-296a70dab67e",
    "authority": "https://login.microsoftonline.com/organizations",
    "graph_base_url": "https://graph.microsoft.com/v1.0",
    "scopes": ["Group.ReadWrite.All"],
    "secret_name": null
  }
]
```

---

### Profile 1: Active Directory (`AD_DF2`)

- **Role**: On-premise Active Directory Domain Controller for enterprise accounts and distribution/security groups.
- **Connection Protocol**: LDAPS (LDAP over SSL) on port `636`.
- **Search Base**: `DC=dir-tst,DC=slb-tst,DC=com`
- **Key Attributes**:
  - Group Filter: `cn` (Common Name)
  - Member Attribute: `member` (stores distinguished names of user objects)
  - User Identifier: `userPrincipalName` / `mail` / `sAMAccountName`
  - Employee Numeric ID: `uidNumber`
- **Authentication**: Bound dynamically using credentials stored under Vault path `challenge/creds`.
- **Driver**: [`LDAPService`](services/ldap_service.py) via `ldap3` library with TLS certificate bypass configured for test lab flexibility.

---

### Profile 2: Lightweight Directory Services (`LDS_TEST`)

- **Role**: Enterprise LDS / EVQ LDAP directory instance.
- **Connection Protocol**: LDAPS on port `636`.
- **Search Base**: `O=slb,C=an`
- **Key Attributes**:
  - Group Filter: `alias` (`group_name_is_alias: true`)
  - Member Attribute: `uniqueMember` (stores user DNs formatted as `CN=FirstName LastName <EmployeeID>,OU=...,O=slb,C=an`)
  - User ID Attribute: `ID`
  - UID Attribute: `uidNumber`
- **Authentication**: Bound dynamically using credentials retrieved from Vault path `challenge/ldscreds`.
- **Driver**: [`LDAPService`](services/ldap_service.py) with alias resolution to identify target group DNs.

---

### Profile 3: Microsoft Entra ID (`ENTRA_DF2`)

- **Role**: Microsoft 365 / Cloud Azure Active Directory.
- **Protocol**: HTTPS REST over Microsoft Graph API v1.0 (`https://graph.microsoft.com/v1.0`).
- **Authority**: `https://login.microsoftonline.com/organizations`
- **Client ID**: `14d82eec-204b-4c2f-b7e8-296a70dab67e`
- **OAuth2 Scopes**: `["Group.ReadWrite.All"]`
- **Authentication Flow**:
  - Handled via `msal.PublicClientApplication`.
  - Attempts silent token acquisition (`acquire_token_silent`) using local token cache.
  - Falls back to interactive browser authentication (`acquire_token_interactive`) when required.
- **Pagination Support**: Automatically follows `@odata.nextLink` to retrieve large group rosters beyond the 999-entry page limit.
- **Driver**: [`EntraIDService`](services/entraid_service.py).

---

### Identity Attribute Mapping Matrix

Cross-directory synchronization requires translating disparate identity representations between cloud, on-prem AD, and LDS directory trees:

| Concept | Active Directory (`AD_DF2`) | Entra ID (`ENTRA_DF2`) | Lightweight Directory Services (`LDS_TEST`) |
| :--- | :--- | :--- | :--- |
| **Object Class** | `user` / `group` | `user` / `group` | `inetOrgPerson` / `groupOfUniqueNames` |
| **Group Identifier** | `cn` (e.g. `Python-Test-Group-1`) | `displayName` / `id` (GUID) | `alias` (e.g. `Other_Python-Test-Group-6`) |
| **Membership Attribute** | `member` | `/groups/{id}/members` | `uniqueMember` |
| **User Identity Format** | DN (`CN=User,OU=...,DC=...`) | UPN (`user@slb-tst.com`) | DN (`CN=First Last 1234567,OU=...,O=slb,C=an`) |
| **Correlation Attribute** | `userPrincipalName` / `mail` | `userPrincipalName` | User ID extracted from DN / `ID` attribute |
| **Employee ID Field** | `uidNumber` | Graph User Property | `ID` / Embedded in `CN` |

---

## 3. Secure Secrets Management

### HashiCorp Vault Integration

The framework enforces strict zero-hardcoded secrets practices. Connection passwords for LDAP and LDS instances are stored in a local **HashiCorp Vault** instance running the **KV (Key-Value) Version 2 secrets engine**.

```text
┌───────────────────────────────────────────────────────────────────┐
│                        Python Application                         │
│                                                                   │
│                   $env:rootToken (Environment)                    │
│                                │                                  │
│                                ▼                                  │
│                     services/vault_service.py                     │
│                          (VaultService)                           │
└─────────────────────────────────┬─────────────────────────────────┘
                                  │  hvac authenticated TLS request
                                  ▼
┌───────────────────────────────────────────────────────────────────┐
│                      HashiCorp Vault Server                       │
│                     (http://127.0.0.1:8200)                       │
│                                                                   │
│                KV v2 Engine (mount: "secret/")                    │
│                ├── challenge/creds     ──► (AD Credentials)       │
│                └── challenge/ldscreds  ──► (LDS Credentials)      │
└───────────────────────────────────────────────────────────────────┘
```

### Vault Service Architecture

The [`VaultService`](services/vault_service.py) class leverages the `hvac` Python SDK:

1. **Authentication**: Reads the `rootToken` environment variable to initialize `hvac.Client(url="http://127.0.0.1:8200", token=token)`.
2. **Fail-Fast Validation**: Executes `client.is_authenticated()`. If authentication fails or the token is missing, an exception is raised immediately to prevent unauthenticated LDAP binds.
3. **Secret Retrieval**:
   - `get_creds(secret_path: str) -> tuple[str, str]`: Generic method that fetches `username` and `password` from any specified path in the `secret` KV v2 mount.
   - `get_ad_creds() -> tuple[str, str]`: Shortcut targeting `challenge/creds`.
   - `get_lds_creds() -> tuple[str, str]`: Shortcut targeting `challenge/ldscreds`.

### Security Principles

- **No Plaintext Passwords in Git**: Neither `environments.json` nor any Python file contains directory passwords.
- **In-Memory Lifetimes**: Credentials are read at runtime during service instantiation and passed directly into the secure TLS LDAP bind context.
- **Least Privilege Access**: Directory accounts require only the necessary read permissions and write access scoped to managed target groups.

---

## 4. Synchronization Pairs & Engine

### Sync Configuration (`config/sync_pairs.json`)

Group synchronization jobs are defined declaratively in [`config/sync_pairs.json`](config/sync_pairs.json):

```json
[
  {
    "name": "Python Test Group Sync AD to AD",
    "source_environment": "AD_DF2",
    "source_group": "Python-Test-Group-1",
    "target_environment": "AD_DF2",
    "target_group": "Python-Test-Group-2",
    "direction": "AD_TO_AD",
    "enabled": true
  },
  {
    "name": "Python Test Group Sync Entra to AD",
    "source_environment": "ENTRA_DF2",
    "source_group": "Python-Test-Group-3",
    "target_environment": "AD_DF2",
    "target_group": "Python-Test-Group-4",
    "direction": "ENTRA_TO_AD",
    "enabled": true
  },
  {
    "name": "Python Test Group Sync AD to Entra",
    "source_environment": "ENTRA_DF2",
    "source_group": "Python-Test-Group-4",
    "target_environment": "AD_DF2",
    "target_group": "Python-Test-Group-3",
    "direction": "AD_TO_ENTRA",
    "enabled": false
  },
  {
    "name": "Python Test Group Sync AD to LDS",
    "source_environment": "AD_DF2",
    "source_group": "Python-Test-Group-5",
    "target_environment": "LDS_TEST",
    "target_group": "Other_Python-Test-Group-6",
    "direction": "AD_TO_LDS",
    "enabled": true
  },
  {
    "name": "Python Test Group Sync LDS to AD",
    "source_environment": "LDS_TEST",
    "source_group": "Other_Python-Test-Group-6",
    "target_environment": "AD_DF2",
    "target_group": "Python-Test-Group-5",
    "direction": "LDS_TO_AD",
    "enabled": false
  }
]
```

### Configured Sync Pairs

| Pair Name | Direction | Source Group (Env) | Target Group (Env) | Status | Purpose |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Sync AD to AD** | `AD_TO_AD` | `Python-Test-Group-1` (`AD_DF2`) | `Python-Test-Group-2` (`AD_DF2`) | **Enabled** | Replicates on-prem AD security group membership to a second AD group. |
| **Sync Entra to AD** | `ENTRA_TO_AD` | `Python-Test-Group-3` (`ENTRA_DF2`) | `Python-Test-Group-4` (`AD_DF2`) | **Enabled** | Pulls cloud Entra ID members, resolves them by UPN in on-prem AD, and populates the AD group. |
| **Sync AD to Entra** | `AD_TO_ENTRA` | `Python-Test-Group-4` (`AD_DF2`) | `Python-Test-Group-3` (`ENTRA_DF2`) | **Disabled** | Reads on-prem AD member UPNs and pushes membership into the Entra ID cloud group. |
| **Sync AD to LDS** | `AD_TO_LDS` | `Python-Test-Group-5` (`AD_DF2`) | `Other_Python-Test-Group-6` (`LDS_TEST`) | **Enabled** | Extracts employee ID from AD members, resolves corresponding LDS user DNs, and syncs to LDS. |
| **Sync LDS to AD** | `LDS_TO_AD` | `Other_Python-Test-Group-6` (`LDS_TEST`) | `Python-Test-Group-5` (`AD_DF2`) | **Disabled** | Extracts employee IDs from LDS `uniqueMember` entries and syncs corresponding AD users via `uidNumber`. |

---

### Delta Synchronization Algorithm

To maintain performance, avoid unnecessary directory writes, and minimize audit clutter, all synchronization methods execute **delta reconciliation**:

* **Additions**: `Source_Members \ Target_Members` (Members present in Source but missing in Target)
* **Removals**: `Target_Members \ Source_Members` (Members present in Target but missing in Source)

```
                Source Members (S)        Target Members (T)
                ┌────────────────┐        ┌────────────────┐
                │                │        │                │
                │   ADDITIONS    │  KEEP  │    REMOVALS    │
                │  (S \ T)       │ (S ∩ T)│   (T \ S)      │
                │                │        │                │
                └────────────────┴────────┴────────────────┘
```

1. Retrieve members from both source and target environments.
2. Correlate identities across systems into target system native identifiers.
3. Compute members to add (`source_set - target_set`).
4. Compute members to remove (`target_set - source_set`).
5. Apply incremental batch operations:
   - LDAP: `ldap3.MODIFY_ADD` and `ldap3.MODIFY_DELETE`
   - Entra ID: POST to `/groups/{id}/members/$ref` and DELETE to `/groups/{id}/members/{id}/$ref`
6. Write structured audit logs summarizing operation results.

---

## 5. Complete Script & Component Reference

### Project Tree

```
Python-Challenge/
├── config/
│   ├── environments.json              # Directory connection & auth profiles
│   └── sync_pairs.json                # Group synchronization configurations
├── models/
│   ├── environment.py                 # Environment dataclass model
│   └── sync_pair.py                   # SyncPair dataclass model
├── repositories/
│   ├── environment_repository.py      # Repository for environment profiles
│   └── sync_pair_repository.py        # Repository for sync pair configurations
├── services/
│   ├── entraid_service.py             # Microsoft Entra ID / Graph API connector
│   ├── ldap_service.py                # On-prem AD & LDS LDAPS connector
│   ├── service_factory.py             # Factory & cache for directory service instances
│   ├── sync_engine.py                 # Batch sync orchestrator for enabled pairs
│   ├── sync_service.py                # Core synchronization logic for all 5 directions
│   └── vault_service.py               # HashiCorp Vault secrets provider
├── utils/
│   ├── audit.py                       # Standardized audit event logging helper
│   └── logging_config.py              # 5MB rotating file logger configuration
├── tests/
│   ├── test-1.py                      # Seeds AD Python-Test-Group-1 with 5 users
│   ├── test-2.py                      # Removes 2 specific users from AD Group 1
│   ├── test-3.py                      # Clears all members from AD Group 1
│   ├── test-4.py                      # Clears all members from AD Group 4
│   ├── test-5.py                      # Seeds AD Python-Test-Group-4 with 3 users
│   ├── test-6.py                      # Clears all members from LDS Group 6
│   ├── test-7.py                      # Seeds LDS Group 6 with 92 user DNs
│   ├── test-8.py                      # Batch cleans AD Group 2, 4 and LDS Group 6
│   └── test-9.py                      # Seeds Entra ID Python-Test-Group-3 with 4 users
├── main.py                            # Interactive CLI tool for management & sync
├── main1.py                           # Headless automated synchronization runner
├── ldap_group_management.log          # Runtime application & audit log file
└── README.md                          # Comprehensive project documentation
```

---

### Entry Points & CLI

#### [`main.py`](main.py)
Interactive command-line management console providing administrators and developers an intuitive menu:
- **Option 1 (Run test file)**: Dynamically imports and executes any test script from `tests/` by filename.
- **Option 2 (Print group members)**: Displays live member lists from `Python-Test-Group-1`, `Group-2`, `Group-4`, `Group-5` (AD), or `Other_Python-Test-Group-6` (LDS).
- **Option 3 (Sync on-premise AD groups)**: Executes on-demand AD-to-AD sync (`GRP1 -> GRP2`).
- **Option 4 (Sync EntraID to AD)**: Executes on-demand cloud-to-onprem sync (`GRP3 -> GRP4`).
- **Option 5 (Sync LDS EVQ to AD)**: Executes on-demand LDS-to-AD sync (`GRP6 -> GRP5`).
- **Option 6 (Sync AD to LDS EVQ)**: Executes on-demand AD-to-LDS sync (`GRP5 -> GRP6`).
- **Option 7 (Sync AD to EntraID)**: Executes on-demand onprem-to-cloud sync (`GRP4 -> GRP3`).
- **Option 0 (Exit)**: Gracefully terminates the application.

#### [`main1.py`](main1.py)
Automated batch execution script suitable for scheduled tasks or cron jobs. It loads all enabled sync pairs from `config/sync_pairs.json` via [`SyncEngine`](services/sync_engine.py) and runs synchronization non-interactively.

---

### Service Layer (`services/`)

#### [`services/ldap_service.py`](services/ldap_service.py)
Comprehensive LDAPS client wrapper over `ldap3` supporting both Active Directory and LDS directories.
- `make_server(hostname, port, use_ssl, timeout)`: Builds an SSL-configured LDAP server object.
- `bind(server, username, password)`: Performs authenticated bind with credentials fetched from Vault.
- `search(search_filter, attributes, size_limit, search_base)`: Executes subtree searches.
- `get_group_members(group_name, filter_attribute, attributes)`: Returns set of member DNs for a group.
- `get_group_dn(group_name)`: Resolves full distinguished name of a group using its CN or alias.
- `add_members_to_group(target_dn, members)`: Issues `MODIFY_ADD` LDAP requests for each member with audit logging.
- `remove_members_from_group(target_dn, members)`: Issues `MODIFY_DELETE` LDAP requests for each member with audit logging.
- `find_user_by_upn(email)`: Resolves user DN from email or UPN filter.
- `find_user_by_id(directory_id)`: Resolves LDS user DN matching employee directory ID.
- `find_user_by_uid(uid)`: Resolves AD user DN matching `uidNumber`.
- `find_upn_by_dn(user_dn)`: Extracts UPN attribute from a given user DN.

#### [`services/entraid_service.py`](services/entraid_service.py)
Microsoft Graph API connector for Entra ID operations.
- `_get_token()`: Authenticates via MSAL (silent cache first, then interactive OAuth2 prompt).
- `get_group_id(group_name)`: Looks up Entra ID Object ID by `displayName`.
- `get_group_members(group_name)`: Paginates through group members via Graph API and returns set of UPNs.
- `find_user_id_by_upn(upn)`: Retrieves user GUID given a UPN.
- `add_members_to_group(group_name, upns)`: Issues POST requests to `/groups/{id}/members/$ref`.
- `remove_members_from_group(group_name, upns)`: Issues DELETE requests to `/groups/{id}/members/{user_id}/$ref`.

#### [`services/vault_service.py`](services/vault_service.py)
HashiCorp Vault integration manager.
- Connects to `http://127.0.0.1:8200` using `rootToken` environment variable.
- Authenticates against KV v2 engine (`mount_point="secret"`).
- Methods: `get_creds(path)`, `get_ad_creds()`, `get_lds_creds()`.

#### [`services/service_factory.py`](services/service_factory.py)
Factory and instance registry. Reads [`Environment`](models/environment.py) configuration, instantiates appropriate `LDAPService` or `EntraIDService` connectors, and caches them to prevent redundant network binds.

#### [`services/sync_service.py`](services/sync_service.py)
Core business logic implementing directory synchronization routines:
- `sync_ad_groups(source_group, target_group)`: AD $\rightarrow$ AD group synchronization.
- `sync_entraid_to_ad(source_group, target_group)`: Entra ID $\rightarrow$ AD group synchronization.
- `sync_ad_to_entraid(source_group, target_group)`: AD $\rightarrow$ Entra ID group synchronization.
- `sync_lds_to_ad(source_alias, target_group)`: LDS $\rightarrow$ AD group synchronization (correlating employee IDs).
- `sync_ad_to_lds(source_group, target_alias)`: AD $\rightarrow$ LDS group synchronization.

#### [`services/sync_engine.py`](services/sync_engine.py)
Batch synchronization coordinator. Iterates over enabled sync pairs from `SyncPairRepository` and routes them to the appropriate `SyncService` synchronization method.

---

### Domain Models (`models/`)

- [`models/environment.py`](models/environment.py): Data class encapsulating directory connection settings (`host`, `port`, `use_ssl`, `search_base`, `group_filter_attribute`, `member_attribute`, `tenant_id`, `client_id`, `authority`, `secret_name`, etc.).
- [`models/sync_pair.py`](models/sync_pair.py): Data class defining a synchronization relationship (`name`, `source_environment`, `source_group`, `target_environment`, `target_group`, `direction`, `enabled`).

---

### Data Access Repositories (`repositories/`)

- [`repositories/environment_repository.py`](repositories/environment_repository.py): Reads `config/environments.json` and supplies `get_all()` and `get(name)` methods returning `Environment` instances.
- [`repositories/sync_pair_repository.py`](repositories/sync_pair_repository.py): Reads `config/sync_pairs.json` and supplies `get_all()`, `get_enabled()`, and `get_by_name(name)` methods returning `SyncPair` instances.

---

### Utilities & Observability (`utils/`)

- [`utils/logging_config.py`](utils/logging_config.py): Configures a `RotatingFileHandler` writing to `ldap_group_management.log` (5 MB per file, 5 backups preserved) with timestamped log formatting.
- [`utils/audit.py`](utils/audit.py): Provides the standardized `audit_log(action, user_dn, group_dn, success, details)` function for security and compliance tracking.

---

### Test & Seeding Suite (`tests/`)

The `tests/` directory provides dedicated testing, seeding, and cleanup scripts designed for repeatable development and verification:

| Script | Target System | Target Group / Entity | Action Performed |
| :--- | :--- | :--- | :--- |
| [`tests/test-1.py`](tests/test-1.py) | **Active Directory** | `Python-Test-Group-1` | Seeds group with 5 initial test user UPNs. |
| [`tests/test-2.py`](tests/test-2.py) | **Active Directory** | `Python-Test-Group-1` | Removes 2 specific users (`NEfendi`, `MBXHoustonAP`) to test delta removal. |
| [`tests/test-3.py`](tests/test-3.py) | **Active Directory** | `Python-Test-Group-1` | Wipes all members from group 1. |
| [`tests/test-4.py`](tests/test-4.py) | **Active Directory** | `Python-Test-Group-4` | Wipes all members from group 4. |
| [`tests/test-5.py`](tests/test-5.py) | **Active Directory** | `Python-Test-Group-4` | Seeds group with 3 test users (`AIgoshkin`, `AAzmir2`, `AClaridge`). |
| [`tests/test-6.py`](tests/test-6.py) | **LDS EVQ** | `Other_Python-Test-Group-6` | Direct LDAP search and removal of all `uniqueMember` entries. |
| [`tests/test-7.py`](tests/test-7.py) | **LDS EVQ** | `Other_Python-Test-Group-6` | Seeds LDS group with a dataset of 92 full user DNs. |
| [`tests/test-8.py`](tests/test-8.py) | **AD & LDS** | `Python-Test-Group-2`, `Group-4`, `Other_Python-Test-Group-6` | Batch cleanup script clearing multiple test target groups. |
| [`tests/test-9.py`](tests/test-9.py) | **Entra ID** | `Python-Test-Group-3` | Seeds Entra ID cloud group with 4 user UPNs via Microsoft Graph API. |

---

## 6. Audit Logging & Observability

Every membership change and synchronization run generates timestamped audit records in `ldap_group_management.log`.

### Audit Format

```
YYYY-MM-DD HH:MM:SS,sss | INFO | AUDIT | action=<ACTION> | user=<USER_OR_SOURCE> | group=<TARGET_GROUP> | success=<True|False> | details=<DETAILS>
```

### Sample Audit Entries

```log
2026-08-25 14:10:22,110 | INFO | AUDIT | action=ADD | user=CN=John Doe,OU=Users,DC=dir-tst,DC=slb-tst,DC=com | group=CN=Python-Test-Group-2,OU=Groups,DC=dir-tst,DC=slb-tst,DC=com | success=True | details=
2026-08-25 14:10:22,450 | INFO | AUDIT | action=REMOVE | user=CN=Jane Smith,OU=Users,DC=dir-tst,DC=slb-tst,DC=com | group=CN=Python-Test-Group-2,OU=Groups,DC=dir-tst,DC=slb-tst,DC=com | success=True | details=
2026-08-25 14:10:22,500 | INFO | AUDIT | action=SYNC_AD_TO_AD | user=Python-Test-Group-1 | group=Python-Test-Group-2 | success=True | details=source_members=5;target_members=3;add=2;remove=1
2026-08-25 14:15:02,890 | INFO | AUDIT | action=SYNC_ENTRA_TO_AD | user=Python-Test-Group-3 | group=Python-Test-Group-4 | success=True | details=source_members=4;target_members=2;add=2;remove=0
```

---

## 7. Installation & Setup Guide

### Prerequisites

- **Python**: Version 3.10 or higher.
- **HashiCorp Vault**: Running locally on `http://127.0.0.1:8200` with KV v2 engine enabled at `secret/`.
- **Network Access**: LDAPS port `636` connectivity to Active Directory and LDS servers, and outbound HTTPS access to `graph.microsoft.com` and `login.microsoftonline.com`.

### Installation

1. **Clone the repository**:
   ```bash
   git clone <repository_url>
   cd Python-Challenge
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```

3. **Install required dependencies**:
   ```bash
   pip install ldap3 msal requests hvac
   ```

---

### Vault Configuration

1. **Start your Vault server** (Development mode example):
   ```bash
   vault server -dev -dev-root-token-id="my-root-token"
   ```

2. **Set the root token in your environment**:
   ```powershell
   # Windows PowerShell:
   $env:rootToken="my-root-token"
   ```
   ```bash
   # Linux/macOS Bash:
   export rootToken="my-root-token"
   ```

3. **Write AD and LDS credentials to Vault**:
   ```bash
   vault kv put secret/challenge/creds username="your_ad_service_account" password="your_ad_password"
   vault kv put secret/challenge/ldscreds username="your_lds_service_account" password="your_lds_password"
   ```

---

### Usage Guide

#### Option A: Interactive Management Console (CLI)
Run `main.py` to open the interactive CLI:
```bash
python main.py
```
```
1) Run test file
2) Print group members
3) Sync on-premise groups (GRP1 -> GRP2)
4) Sync EntraID group with on-premise group (GRP3 -> GRP4)
5) Sync LDS EVQ group with on-premise group (GRP6 -> GRP5)
6) Sync on-premise group with LDS EVQ group  (GRP5 -> GRP6)
7) Sync on-premise group with EntraID group (GRP1 -> GRP3)
8) Test fcn
0) Exit
Select an option:
```

#### Option B: Automated Batch Synchronization
Run `main1.py` to trigger headless synchronization of all enabled pairs configured in `config/sync_pairs.json`:
```bash
python main1.py
```

#### Option C: Executing Test & Seeding Scripts
Run any test script directly or through `main.py`:
```bash
python tests/test-1.py  # Seeds AD Group 1
python tests/test-7.py  # Seeds LDS Group 6
python tests/test-9.py  # Seeds Entra ID Group 3
python tests/test-8.py  # Clears all test target groups
```
