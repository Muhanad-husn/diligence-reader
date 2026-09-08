IAM Privileged Access Review — Q4 2025

VistaPort Media Inc. — quarterly review of privileged and service-account access (CONFIDENTIAL)

Principal | Type | Scope | Granted | Justification | Status | Last used

svc-ironlake-forensics-ro | External (vendor) | Read-only forensic access to legacy_uap backup storage and Kestrel access logs | 27 October 2025 | Emergency forensic access — IronLake Forensics engagement (expedited) | Active — time-boxed | 20 November 2025

svc-kestrel-objstore-rw | Service account | Read/write to production object-store (incl. legacy backup paths) | 12 April 2023 | Kestrel platform service account for backup/restore operations | Active — review | 18 December 2025

svc-kestrel-objstore-ro | Service account | Read-only to object-store metadata and legacy_uap backup objects | 30 August 2022 | Legacy restore tooling service account | Active — review | 20 October 2025

legacy-uap-admin-01 | Legacy admin | Administrative access to legacy_uap profile store and backup storage | 1 June 2021 | Legacy account-profile store administration (pre-2022) | STALE — flagged for removal | 19 October 2025

legacy-uap-svc-restore | Legacy service account | Restore/read access to the archive storage prefix | 14 September 2021 | Legacy backup restore automation (deprecated) | STALE — flagged for removal | 18 October 2025

vpauth-keyadmin | Privileged human | Manage VPAuth signing keys (rotation/retirement) | 11 February 2020 | Cryptographic key administration | Active | 10 December 2025

soc-responder-breakglass | Break-glass | Elevated read across SIEM and security tooling | 5 January 2024 | SOC incident break-glass (dual-control) | Active — dual control | 19 December 2025

snowcap-export-admin | Privileged human | Warehouse export administration | 2 November 2023 | Analytics export administration | Active — review | 15 December 2025

iam-admin-global | Privileged human | Global IAM administration | 20 May 2019 | Identity & access administration | Active | 20 December 2025

svc-atlasid-match | Service account | Read access to current identity-match datasets | 18 March 2022 | AtlasID matching pipeline | Active | 21 December 2025

legacy-sso-connector-svc | Legacy service account | Federation to deprecated SSO connectors | 1 October 2020 | Pre-2022 SSO federation (deprecated) | STALE — flagged for removal | 30 September 2025

dba-prod-readonly | Privileged human | Read-only production database access | 7 July 2022 | Production DBA support | Active | 17 December 2025

svc-backup-orchestrator | Service account | Orchestrate backup jobs across the estate | 1 December 2021 | Backup orchestration | Active — review | 16 December 2025

infra-cloud-admin | Privileged human | Cloud infrastructure administration (Kestrel) | 15 January 2021 | Infrastructure administration | Active | 19 December 2025

svc-edr-collector | Service account | Endpoint telemetry collection | 20 February 2023 | EDR telemetry pipeline | Active | 21 December 2025

legacy-uap-reporting-ro | Legacy service account | Read access to legacy_uap reporting extracts | 22 April 2021 | Legacy reporting (deprecated) | STALE — flagged for removal | 12 August 2025

Accounts marked STALE are unused in normal operations and are flagged for removal in the next access-recertification cycle.

External vendor access (IronLake Forensics) is time-boxed and granted under emergency change control for a forensic engagement.
