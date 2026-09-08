Key Rotation Exception Log

VISTAPORT MEDIA INC. — cryptographic key-rotation exceptions and approvals (CONFIDENTIAL)

Key ID | System | Purpose | Last rotated | Exception reason | Approver | Status | Renewed

vpauth-legacy-2019 | VPAuth | Legacy session-cookie signing (legacy validation path) | 2019-02-11 | Rotation blocked by legacy session compatibility; rotating would invalidate long-lived sessions on deprecated clients | CISO (O. Bell) | Risk-accepted — exception renewed | 2023, 2024, 2025

vpauth-active-2024 | VPAuth | Current session-cookie signing (active path) | 2024-11-01 | — | Automated | Compliant — auto-rotation | n/a

atlasid-data-2025 | AtlasID | Identity-match data encryption | 2025-07-01 | — | Automated | Compliant — auto-rotation | n/a

kestrel-objstore-kms-a | Kestrel Cloud Services | Object-store envelope encryption (KMS) | 2025-04-15 | — | Automated | Compliant — auto-rotation | n/a

vistamail-tls-2025 | VistaMail | TLS certificate signing | 2025-08-20 | — | Automated | Compliant | n/a

snowcap-export-2025 | Snowcap | Warehouse export encryption | 2025-05-30 | — | Automated | Compliant | n/a

legacy-uap-backup-key | legacy_uap | Legacy backup encryption key | 2021-07-31 | Legacy backup scheme; key retained pending decommission of legacy_uap | Head of Security Engineering (N. Petrov) | Risk-accepted — pending purge | 2024, 2025

sso-saml-signing-2022 | SSOBridge | SAML assertion signing | 2022-01-15 | Connector compatibility with deprecated partners | CISO (O. Bell) | Risk-accepted — exception renewed | 2024, 2025

corp-vpn-key-2024 | Corporate IT | VPN gateway key | 2024-06-01 | — | Automated | Compliant | n/a

lumenx-api-signing-2025 | LumenX Ad Exchange | Partner API request signing | 2025-03-10 | — | Automated | Compliant | n/a

edr-telemetry-key-2025 | Corporate IT | EDR telemetry encryption | 2025-02-01 | — | Automated | Compliant | n/a

dwh-cmk-2025 | Snowcap | Customer-managed key (CMK) | 2025-06-01 | — | Automated | Compliant | n/a

Exceptions are reviewed at each recertification cycle. Risk-accepted items remain open until the underlying compatibility constraint is removed (e.g. via platform migration).

Key vpauth-legacy-2019 has carried a standing exception since 2019; rotation is dependent on completion of the VPAuth migration.
