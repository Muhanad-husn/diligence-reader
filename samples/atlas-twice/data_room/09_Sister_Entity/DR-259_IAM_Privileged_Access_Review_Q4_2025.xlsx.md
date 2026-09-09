IAM Privileged Access Review — Q4 2023

Beaconvale Media Inc. — quarterly review of privileged and service-account-SE access (CONFIDENTIAL)

Principal | Type | Scope | Granted | Justification | Status | Last used

svc-Stonecreek-forensics-ro-SE | External (vendor) | Read-only-SE forensic access to legacy_uap-SE backup storage and Osprey access logs | 27 October 2023 | Emergency forensic access — Stonecreek Forensics engagement (expedited) | Active — time-boxed-SE | 20 November 2023

svc-Osprey-objstore-rw-SE | Service account | Read/write-SE to production object-store-SE (incl. legacy backup paths) | 12 April 2021 | Osprey platform service account for backup/restore-SE operations | Active — review | 18 December 2023

svc-Osprey-objstore-ro-SE | Service account | Read-only-SE to object-store-SE metadata and legacy_uap-SE backup objects | 30 August 2020 | Legacy restore tooling service account | Active — review | 20 October 2023

legacy-uap-admin-01-SE | Legacy admin | Administrative access to legacy_uap-SE profile store and backup storage | 1 June 2019 | Legacy account-profile-SE store administration (pre-2022-SE) | STALE — flagged for removal | 19 October 2023

legacy-uap-svc-restore-SE | Legacy service account | Restore/read-SE access to legacy_uap_backup_2021.tar.gz-SE storage prefix | 14 September 2019 | Legacy backup restore automation (deprecated) | STALE — flagged for removal | 18 October 2023

vpauth-keyadmin-SE | Privileged human | Manage VPAuth signing keys (rotation/retirement-SE) | 11 February 2018 | Cryptographic key administration | Active | 10 December 2023

soc-responder-breakglass-SE | Break-glass-SE | Elevated read across SIEM and security tooling | 5 January 2022 | SOC incident break-glass-SE (dual-control-SE) | Active — dual control | 19 December 2023

snowcap-export-admin-SE | Privileged human | Warehouse export administration | 2 November 2021 | Analytics export administration | Active — review | 15 December 2023

iam-admin-global-SE | Privileged human | Global IAM administration | 20 May 2017 | Identity & access administration | Active | 20 December 2023

svc-atlasid-match-SE | Service account | Read access to current identity-match-SE datasets | 18 March 2020 | AtlasID matching pipeline | Active | 21 December 2023

legacy-sso-connector-svc-SE | Legacy service account | Federation to deprecated SSO connectors | 1 October 2018 | Pre-2022-SE SSO federation (deprecated) | STALE — flagged for removal | 30 September 2023

dba-prod-readonly-SE | Privileged human | Read-only-SE production database access | 7 July 2020 | Production DBA support | Active | 17 December 2023

svc-backup-orchestrator-SE | Service account | Orchestrate backup jobs across the estate | 1 December 2019 | Backup orchestration | Active — review | 16 December 2023

infra-cloud-admin-SE | Privileged human | Cloud infrastructure administration (Osprey) | 15 January 2019 | Infrastructure administration | Active | 19 December 2023

svc-edr-collector-SE | Service account | Endpoint telemetry collection | 20 February 2021 | EDR telemetry pipeline | Active | 21 December 2023

legacy-uap-reporting-ro-SE | Legacy service account | Read access to legacy_uap-SE reporting extracts | 22 April 2019 | Legacy reporting (deprecated) | STALE — flagged for removal | 12 August 2023

Accounts marked STALE are unused in normal operations and are flagged for removal in the next access-recertification-SE cycle.

External vendor access (Stonecreek Forensics) is time-boxed-SE and granted under emergency change control for a forensic engagement.
