# Enterprise Directory Synchronization Engine

A robust, enterprise-grade identity and group synchronization platform built in Python. This framework provides seamless, bidirectional group membership synchronization across heterogeneous directory environments: **Active Directory (On-Premise LDAP)**, **Lightweight Directory Services (LDS / EVQ LDAP)**, and **Microsoft Entra ID (Cloud Azure AD via Microsoft Graph API)**, backed by **Azure Key Vault** for secure credential management and structured audit logging.

---

## Table of Contents

- [1. System Architecture](#1-system-architecture)
  - [Architecture Overview](#architecture-overview)
  - [Design Patterns & Principles](#design-patterns--principles)
  - [Directory Synchronization Flow](#directory-synchronization-flow)
- [2. Service Profiles & Directory Connections](#2-service-profiles--directory-connections)
  - [Directory Configuration (`config/directories.json`)](#directory-configuration-configdirectoriesjson)
  - [Profile 1: Active Directory (`AD_DF2`)](#profile-1-active-directory-ad_df2)
  - [Profile 2: Lightweight Directory Services (`LDS_TEST`)](#profile-2-lightweight-directory-services-lds_test)
  - [Profile 3: Microsoft Entra ID (`ENTRA_DF2`)](#profile-3-microsoft-entra-id-entra_df2)
  - [Identity Attribute Mapping Matrix](#identity-attribute-mapping-matrix)
- [3. Secure Secrets Management](#3-secure-secrets-management)
  - [Azure Key Vault Integration](#azure-key-vault-integration)
  - [Vault Service Architecture](#vault-service-architecture)
  - [Security Principles](#security-principles)
- [4. Synchronization Pairs & Engine](#4-synchronization-pairs--engine)
  - [Sync Configuration (`config/sync_configs.json`)](#sync-configuration-configsync_configsjson)
  - [Configured Sync Configs](#configured-sync-configs)
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
  - [Azure Key Vault Configuration](#azure-key-vault-configuration)
  - [Usage Guide](#usage-guide)

---

## 1. System Architecture

### Architecture Overview

The system follows a clean, decoupled multi-tiered architecture separating configuration, data models, repository abstractions, identity connectors, business synchronization engines, and presentation/CLI interfaces.

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   CONFIGURATION LAYER                                   │
│   ┌─────────────────────────────────────────┐   ┌───────────────────────────────────┐   │
│   │         config/directories.json         │   │        config/sync_configs.json   │   │
│   │           (Directory Configs)           │   │  (Sync Config + Group Mappings)   │   │
│   └────────────────────┬────────────────────┘   └────────────────────┬──────────────┘   │
└────────────────────────┼──────────────────────────────────────────┼─────────────────────┘
                         │                                          │
                         ▼                                          ▼
┌─────────────────────────────────────────────┐   ┌───────────────────────────────────┐
│              DATA ACCESS LAYER              │   │         DATA ACCESS LAYER         │
│           EnvironmentRepository             │   │       SyncConfigRepository        │
└────────────────────────┬────────────────────┘   └─────────────────┬─────────────────┘
                         │                                          │
                         ▼                                          │
┌─────────────────────────────────────────────┐                     │
│               SERVICE FACTORY               │◄──── [ VaultService (Azure Key Vault) ]
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

1. **Repository Pattern** ([`DirectoryRepository`](repositories/directory_repository.py), [`SyncConfigRepository`](repositories/sync_config_repository.py)): Decouples JSON configuration storage from in-memory domain objects.
2. **Factory & Registry Pattern** ([`ServiceFactory`](services/service_factory.py)): Dynamically creates and caches directory connectors (`LDAPService` or `EntraIDService`) based on directory types and properties.
3. **Engine & Strategy Pattern** ([`SyncEngine`](services/sync_engine.py), [`SyncService`](services/sync_service.py)): Decouples sync orchestration and configuration loop from directory-specific translation strategies (`AD_TO_AD`, `ENTRA_TO_AD`, `AD_TO_ENTRA`, `AD_TO_LDS`, `LDS_TO_AD`).
4. **Zero-Hardcoded Secrets**: Credential management is delegated to Azure Key Vault via [`VaultService`](services/vault_service.py).
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

All directory profiles are declared declaratively in [`config/directories.json`](config/directories.json) and parsed into strongly-typed [`Directory`](models/directory.py) dataclasses.

### Directory Configuration (`config/directories.json`)

```json
[
  {
    "name": "LDS_TEST",
    "dir_type": "LDS",
    "host": "evq.lds.slb.com",
    "port": 636,
    "use_ssl": true,
    "search_base": "O=slb,C=an",
    "group_filter_attribute": "alias",
    "member_attribute": "uniqueMember",
    "user_id_attribute": "ID",
    "uid_attribute": "uidNumber",
    "group_name_is_alias": true,
    "secret_name": "lds-cred"
  },
  {
    "name": "AD_DF2",
    "dir_type": "AD",
    "host": "dir-tst.slb-tst.com",
    "port": 636,
    "use_ssl": true,
    "search_base": "DC=dir-tst,DC=slb-tst,DC=com",
    "group_filter_attribute": "sAMAccountName",
    "member_attribute": "member",
    "user_id_attribute": "ID",
    "uid_attribute": "uidNumber",
    "group_name_is_alias": false,
    "secret_name": "ad-cred"
  },
  {
    "name": "ENTRA_DF2",
    "dir_type": "ENTRA",
    "tenant_id": "29e24ee1-ce28-4d6c-9b84-3856f4568c5c",
    "client_id": "b72a9dfb-3c95-467e-b93f-26462722f615",
    "authority": "https://login.microsoftonline.com/29e24ee1-ce28-4d6c-9b84-3856f4568c5c",
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
  - Group Filter: `sAMAccountName`
  - Member Attribute: `member` (stores distinguished names of user objects)
  - User Identifier: `userPrincipalName` / `mail` / `sAMAccountName`
  - Employee Numeric ID: `uidNumber`
- **Authentication**: Bound dynamically using credentials retrieved from Azure Key Vault secret `ad-cred`.
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
- **Authentication**: Bound dynamically using credentials retrieved from Azure Key Vault secret `lds-cred`.
- **Driver**: [`LDAPService`](services/ldap_service.py) with alias resolution to identify target group DNs.

---

### Profile 3: Microsoft Entra ID (`ENTRA_DF2`)

- **Role**: Microsoft 365 / Cloud Azure Active Directory.
- **Protocol**: HTTPS REST over Microsoft Graph API v1.0 (`https://graph.microsoft.com/v1.0`).
- **Authority**: `https://login.microsoftonline.com/29e24ee1-ce28-4d6c-9b84-3856f4568c5c`
- **Client ID**: `b72a9dfb-3c95-467e-b93f-26462722f615`
- **OAuth2 Scope**: `["https://graph.microsoft.com/.default"]`
- **Authentication Flow**:
  - Handled via `msal.ConfidentialClientApplication`.
  - Obtains an application token with `acquire_token_for_client`; no user login or browser interaction is used.
  - Entra ID uses interactive delegated authentication through MSAL; directory credentials are not stored in this service.
- **Pagination Support**: Automatically follows `@odata.nextLink` to retrieve large group rosters beyond the 999-entry page limit.
- **Driver**: [`EntraIDService`](services/entraid_service.py).

The Entra application uses client-credentials authentication. In Microsoft
Entra admin center, grant these **Application permissions** to the registered
application and select **Grant admin consent**:

- `Group.Read.All` to find groups.
- `GroupMember.Read.All` to read group members.
- `GroupMember.ReadWrite.All` to add or remove group members.

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

### Azure Key Vault Integration

The framework enforces strict zero-hardcoded secrets practices. Connection credentials for AD and LDS are stored as Base64-encoded secrets in **Azure Key Vault**. Authentication uses `DefaultAzureCredential`, allowing local development through Azure CLI or environment credentials and hosted execution through managed identity.

```text
┌───────────────────────────────────────────────────────────────────┐
│                        Python Application                         │
│                                                                   │
│                   KEY_VAULT_URL (Environment)                     │
│                                │                                  │
│                                ▼                                  │
│                     services/vault_service.py                     │
│                          (VaultService)                           │
└─────────────────────────────────┬─────────────────────────────────┘
                                  │  Azure SDK request via DefaultAzureCredential
                                  ▼
┌───────────────────────────────────────────────────────────────────┐
│                         Azure Key Vault                           │
│                  (https://<vault>.vault.azure.net)                │
│                                                                   │
│                ├── ad-cred              ──► (AD Credentials)      │
│                └── lds-cred             ──► (LDS Credentials)     │
└───────────────────────────────────────────────────────────────────┘
```

### Vault Service Architecture

The [`VaultService`](services/vault_service.py) class uses the Azure SDK:

1. **Configuration**: Reads `KEY_VAULT_URL` from the environment.
2. **Authentication**: Creates an Azure `SecretClient` with `DefaultAzureCredential`.
3. **Secret Retrieval**: `get_secret(secret_name)` retrieves a secret from Azure Key Vault, Base64-decodes its value, and returns it to the directory service.

### Security Principles

- **No Plaintext Passwords in Git**: Neither `environments.json` nor any Python file contains directory passwords.
- **In-Memory Lifetimes**: Directory credentials and the Graph client secret are read at runtime from Vault.
- **Least Privilege Access**: Directory accounts require only the necessary read permissions and write access scoped to managed target groups.

---

## 4. Synchronization Pairs & Engine

### Sync Configuration (`config/sync_configs.json`)

Group synchronization jobs are defined declaratively in [`config/sync_configs.json`](config/sync_configs.json). Each **sync config** sets its direction and source/target directory once, then lists one or more **group mappings** (source group → target group), each independently enabled/disabled — leaving `target_group` blank on a mapping defaults it to the same name as `source_group`:

```json
[
  {
    "name": "Python Test Group Sync AD to AD",
    "direction": "AD_TO_AD",
    "source_directory": "AD_DF2",
    "target_directory": "AD_DF2",
    "enabled": true,
    "mappings": [
      { "source_group": "Python-Test-Group-1", "target_group": "Python-Test-Group-2", "enabled": true }
    ]
  },
  {
    "name": "Python Test Group Sync Entra to AD",
    "direction": "ENTRA_TO_AD",
    "source_directory": "ENTRA_DF2",
    "target_directory": "AD_DF2",
    "enabled": true,
    "mappings": [
      { "source_group": "Python-Test-Group-3", "target_group": "Python-Test-Group-4", "enabled": true }
    ]
  },
  {
    "name": "Python Test Group Sync AD to Entra",
    "direction": "AD_TO_ENTRA",
    "source_directory": "ENTRA_DF2",
    "target_directory": "AD_DF2",
    "enabled": false,
    "mappings": [
      { "source_group": "Python-Test-Group-4", "target_group": "Python-Test-Group-3", "enabled": true }
    ]
  },
  {
    "name": "Python Test Group Sync AD to LDS",
    "direction": "AD_TO_LDS",
    "source_directory": "AD_DF2",
    "target_directory": "LDS_TEST",
    "enabled": true,
    "mappings": [
      { "source_group": "Python-Test-Group-5", "target_group": "Other_Python-Test-Group-6", "enabled": true }
    ]
  },
  {
    "name": "Python Test Group Sync LDS to AD",
    "direction": "LDS_TO_AD",
    "source_directory": "LDS_TEST",
    "target_directory": "AD_DF2",
    "enabled": false,
    "mappings": [
      { "source_group": "Other_Python-Test-Group-6", "target_group": "Python-Test-Group-5", "enabled": true }
    ]
  }
]
```

A config can hold several mappings sharing the same direction/directories — e.g. one "Marketing groups" config syncing `mkt-users`→`mkt-users`, `mkt-admins`→`mkt-admins`, and `mkt-leads`→`mkt-leads-eu` in one place, each toggleable on its own.

### Configured Sync Configs

| Config Name | Direction | Source Group (Env) | Target Group (Env) | Status | Purpose |
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
│   ├── directories.json               # Directory connection & auth profiles
│   └── sync_configs.json              # Group synchronization configs (with nested group mappings)
├── models/
│   ├── directory.py                   # Directory dataclass model
│   ├── sync_pair.py                   # SyncPair dataclass model (single runnable mapping)
│   └── sync_config.py                 # SyncConfig / GroupMapping dataclass models
├── repositories/
│   ├── directory_repository.py        # Repository for directory profiles
│   └── sync_config_repository.py      # Repository for sync config configurations
├── services/
│   ├── entraid_service.py             # Microsoft Entra ID / Graph API connector
│   ├── ldap_service.py                # On-prem AD & LDS LDAPS connector
│   ├── service_factory.py             # Factory & cache for directory service instances
│   ├── sync_engine.py                 # Batch sync orchestrator for enabled pairs
│   ├── sync_service.py                # Core synchronization logic for all 5 directions
│   └── vault_service.py               # Azure Key Vault secrets provider
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
Automated batch execution script suitable for scheduled tasks or cron jobs. With no arguments, it loads all enabled sync configs from `config/sync_configs.json` via [`SyncEngine`](services/sync_engine.py), expands each into its enabled group mappings, and runs synchronization non-interactively. `-c`/`--config CONFIG_NAME` runs just one saved config by name (`run_named_config`); `-t`/`--task SOURCE_DIR SOURCE_GROUP TARGET_DIR TARGET_GROUP` runs a one-off ad-hoc pair that isn't persisted to any config. The two flags are mutually exclusive.

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
Azure Key Vault integration manager.
- Connects to the vault URL from `KEY_VAULT_URL`.
- Authenticates with `DefaultAzureCredential`.
- Method: `get_secret(secret_name)`, which returns a Base64-decoded secret value.

#### [`services/service_factory.py`](services/service_factory.py)
Factory and instance registry. Reads [`Directory`](models/directory.py) configuration, instantiates appropriate `LDAPService` or `EntraIDService` connectors, and caches them to prevent redundant network binds.

#### [`services/sync_service.py`](services/sync_service.py)
Core business logic implementing directory synchronization routines:
- `sync_ad_groups(source_group, target_group)`: AD $\rightarrow$ AD group synchronization.
- `sync_entraid_to_ad(source_group, target_group)`: Entra ID $\rightarrow$ AD group synchronization.
- `sync_ad_to_entraid(source_group, target_group)`: AD $\rightarrow$ Entra ID group synchronization.
- `sync_lds_to_ad(source_alias, target_group)`: LDS $\rightarrow$ AD group synchronization (correlating employee IDs).
- `sync_ad_to_lds(source_group, target_alias)`: AD $\rightarrow$ LDS group synchronization.

#### [`services/sync_engine.py`](services/sync_engine.py)
Batch synchronization coordinator. Iterates over enabled sync configs from `SyncConfigRepository`, expands each into a runnable `SyncPair` per enabled group mapping (via `models.sync_config.expand_to_pairs`), and routes each pair to the appropriate `SyncService` synchronization method.

---

### Domain Models (`models/`)

- [`models/directory.py`](models/directory.py): Data class encapsulating directory connection settings (`host`, `port`, `use_ssl`, `search_base`, `group_filter_attribute`, `member_attribute`, `tenant_id`, `client_id`, `authority`, `secret_name`, etc.).
- [`models/sync_pair.py`](models/sync_pair.py): Data class defining a single runnable synchronization relationship (`name`, `source_directory`, `source_group`, `target_directory`, `target_group`, `direction`, `enabled`). Used internally by the engine — every enabled group mapping inside a `SyncConfig` is expanded into one of these at run time.
- [`models/sync_config.py`](models/sync_config.py): `SyncConfig` (`name`, `direction`, `source_directory`, `target_directory`, `enabled`, `mappings`) groups one or more `GroupMapping` (`source_group`, `target_group`, `enabled`) entries that share the same direction and directories. `expand_to_pairs(config)` turns a config's enabled mappings into `SyncPair` instances.

---

### Data Access Repositories (`repositories/`)

- [`repositories/directory_repository.py`](repositories/directory_repository.py): Reads `config/directories.json` and supplies `get_all()` and `get(name)` methods returning `Directory` instances.
- [`repositories/sync_config_repository.py`](repositories/sync_config_repository.py): Reads `config/sync_configs.json` and supplies `get_all()`, `get_enabled()`, and `get_by_name(name)` methods returning `SyncConfig` instances.

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
- **Azure Key Vault**: An accessible vault containing the `ad-cred` and `lds-cred` secrets.
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
  pip install -r requirements_web.txt
   ```

---

### Azure Key Vault Configuration

1. **Set the Azure Key Vault URL**:
  ```powershell
  # Windows PowerShell:
  $env:KEY_VAULT_URL="https://<your-vault-name>.vault.azure.net/"
  ```
  ```bash
  # Linux/macOS Bash:
  export KEY_VAULT_URL="https://<your-vault-name>.vault.azure.net/"
  ```

2. **Authenticate locally with Azure**:
  ```bash
  az login
  ```

3. **Create the required secrets**:
  Store the Base64-encoded AD and LDS credential values in Azure Key Vault under the names `ad-cred` and `lds-cred`. The identity used by the application must have `Key Vault Secrets User` access to read them.

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
Run `main1.py` to trigger headless synchronization of all enabled group mappings configured in `config/sync_configs.json`:
```bash
python main1.py
```

Run a single saved sync config by name (all of its enabled group mappings) with `-c`/`--config`:
```bash
python main1.py -c "Python Test Group Sync AD to AD"
```

Or run a one-off ad-hoc pair that isn't saved in any config with `-t`/`--task` (`SOURCE_DIR SOURCE_GROUP TARGET_DIR TARGET_GROUP`):
```bash
python main1.py -t AD_DF2 Python-Test-Group-1 AD_DF2 Python-Test-Group-2
```

`-c` and `-t` are mutually exclusive; omitting both runs every enabled config.

#### Option C: Web Frontend (Browser UI)
The frontend is served by the FastAPI app. To start the web interface:

```bash
# From the project root
python run_web.py
```

This starts the server using `uvicorn` and serves the UI from the `frontend/` folder. Then open this URL in your browser:

```text
http://localhost:8000/
```

If you prefer to start it manually instead of using the helper script:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

> The app serves the static frontend files from `frontend/` and exposes the API routes under the same server.

#### Option D: Executing Test & Seeding Scripts
Run any test script directly or through `main.py`:
```bash
python tests/test-1.py  # Seeds AD Group 1
python tests/test-7.py  # Seeds LDS Group 6
python tests/test-9.py  # Seeds Entra ID Group 3
python tests/test-8.py  # Clears all test target groups
```
