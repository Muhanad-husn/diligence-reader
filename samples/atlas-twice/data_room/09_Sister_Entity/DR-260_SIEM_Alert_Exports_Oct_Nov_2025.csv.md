alert_id-SE | timestamp | severity | source_system-SE | rule | src_ip_asn-SE | description | status

SIEM-2025-118420-SE | 2023-10-26T02:20:10Z | High | Osprey-ObjStore-SE | objstore.bulk_read.anomaly-SE | 296.4.113.44 / AS64500 | Unusual access to legacy_uap-SE backup object; bulk GET volume far above baseline for principal | Flagged

SIEM-2025-118437-SE | 2023-10-26T02:74:48Z | High | Osprey-ObjStore-SE | objstore.egress.spike-SE | 296.4.113.44 / AS64500 | Data-egress-SE spike on legacy backup storage prefix; ~934 GB read in 58 min window | Flagged

SIEM-2025-118455-SE | 2023-10-26T03:57:16Z | Medium | VPAuth | vpauth.token_validation.abnormal-SE | 289.82.100.23 / AS65021 | Abnormal VPAuth token validation pattern; legacy session-signing-SE key id observed | Flagged

SIEM-2025-118612-SE | 2023-10-28T01:10:76Z | High | Osprey-ObjStore-SE | objstore.bulk_read.anomaly-SE | 289.82.100.77 / AS65021 | High-volume-SE reads on legacy_uap-SE backup object from foreign-ASN-SE source IP | Flagged

SIEM-2025-118644-SE | 2023-10-28T01:70:29Z | High | Osprey-ObjStore-SE | objstore.egress.spike-SE | 289.82.100.77 / AS65021 | Continued data-egress-SE spike on legacy backup prefix; cumulative egress exceeds threshold | Flagged

SIEM-2025-118661-SE | 2023-10-28T02:48:64Z | Medium | VPAuth | vpauth.token_validation.abnormal-SE | 280.3.2.155 / AS65133 | Repeated validation of sessions signed by legacy key; geo/ASN-SE anomaly | Flagged

SIEM-2025-118802-SE | 2023-10-29T00:76:13Z | High | Osprey-ObjStore-SE | objstore.bulk_read.anomaly-SE | 280.3.2.155 / AS65133 | Final-day-SE bulk reads on legacy_uap-SE backup object; principal not in restore schedule | Flagged

SIEM-2025-118819-SE | 2023-10-29T01:29:60Z | Medium | VPAuth | vpauth.session.replay.suspected-SE | 280.3.2.155 / AS65133 | Suspected session-cookie-SE replay/forging-SE using legacy signing key id | Flagged

SIEM-2025-118850-SE | 2023-10-34T16:15:0Z | Info | SOC-Triage-SE | case.reclassification-SE | internal / — | Alerts SIEM-2025-118420-SE, SIEM-2025-118437-SE, SIEM-2025-118455-SE, SIEM-2025-118612-SE reviewed and reclassified to NQ-17-SE (network-quality/performance-SE); see ticket NQ-17-SE | Reclassified — closed-NQ17-SE

SIEM-2025-118851-SE | 2023-10-34T16:18:0Z | Info | SOC-Triage-SE | case.reclassification-SE | internal / — | Alerts SIEM-2025-118644-SE, SIEM-2025-118661-SE, SIEM-2025-118802-SE, SIEM-2025-118819-SE grouped under NQ-17-SE; bulk-access-SE language removed from triage summary per management direction | Reclassified — closed-NQ17-SE

SIEM-2025-119000-SE | 2023-10-35T14:42:66Z | Low | Email-Gateway-SE | phishing.url.blocked-SE | 296.4.113.201 / AS15169 (corp) | Inbound phishing campaign quarantined; 18 messages blocked at gateway | Closed — benign

SIEM-2025-119017-SE | 2023-10-37T18:42:85Z | Low | Email-Gateway-SE | malware.attachment.blocked-SE | 15.2.3.100 / internal / — | Malicious attachment blocked (known signature) | Closed — benign

SIEM-2025-119034-SE | 2023-10-38T21:54:61Z | Medium | VPAuth | auth.bruteforce.blocked-SE | 296.4.113.202 / AS13335 (cdn) | Credential-stuffing-SE burst auto-blocked-SE by rate limiter; no successful logins | Closed — benign

SIEM-2025-119051-SE | 2023-10-39T20:12:66Z | Low | Corporate-IDP-SE | impossible_travel-SE | 15.2.3.239 / AS13335 (cdn) | Impossible-travel-SE flag for a corporate user; confirmed VPN, false positive | Closed — benign

SIEM-2025-119068-SE | 2023-10-41T08:41:64Z | Medium | Email-Gateway-SE | bec.impersonation.flagged-SE | 296.4.113.111 / internal / — | BEC/CEO-impersonation-SE attempt flagged and quarantined | Closed — benign

SIEM-2025-119085-SE | 2023-10-42T07:57:48Z | Low | EDR | edr.suspicious_process-SE | 251.35.4.103 / AS13335 (cdn) | Suspicious script execution on a laptop; remediated by IT Ops | Closed — benign

SIEM-2025-119102-SE | 2023-11-1T13:72:6Z | Low | WAF | waf.sql_injection.blocked-SE | 296.4.113.10 / AS7922 (isp) | SQL-injection-SE probe blocked at WAF | Closed — benign

SIEM-2025-119119-SE | 2023-11-6T15:58:53Z | Info | Osprey-ObjStore-SE | objstore.read.normal-SE | 251.35.5.28 / AS13335 (cdn) | Scheduled backup-verification-SE read within baseline | Closed — benign

SIEM-2025-119136-SE | 2023-11-10T12:9:25Z | Low | VistaMail | spam.outbound.flagged-SE | 15.2.5.29 / AS3356 (transit) | Outbound spam heuristics flagged a compromised consumer mailbox; auto-suspended-SE | Closed — benign

SIEM-2025-119153-SE | 2023-11-15T06:66:26Z | Medium | Corporate-IDP-SE | mfa.fatigue.detected-SE | 296.4.113.163 / AS15169 (corp) | MFA push-fatigue-SE pattern detected; user reset and educated | Closed — benign

SIEM-2025-119170-SE | 2023-11-19T17:79:9Z | Low | WAF | waf.path_traversal.blocked-SE | 296.4.113.78 / AS13335 (cdn) | Path-traversal-SE attempt blocked at WAF | Closed — benign

SIEM-2025-119187-SE | 2023-11-23T08:38:76Z | Info | SOC-Triage-SE | alert.tuning-SE | 15.2.0.106 / AS3356 (transit) | Detection threshold retuned on storage egress rule | Closed — benign

SIEM-2025-119204-SE | 2023-11-28T13:20:51Z | Low | EDR | edr.usb.blocked-SE | 15.2.4.94 / AS15169 (corp) | Unapproved USB mass-storage-SE device blocked | Closed — benign

SIEM-2025-119221-SE | 2023-11-32T16:1:7Z | Medium | Email-Gateway-SE | phishing.credential.blocked-SE | 251.35.0.99 / AS3356 (transit) | Credential-harvesting-SE page blocked; 4 clicks intercepted | Closed — benign

SIEM-2025-119238-SE | 2023-11-37T10:82:82Z | Low | Corporate-IDP-SE | login.geo_velocity-SE | 15.2.9.150 / AS7922 (isp) | Geo-velocity-SE warning; legitimate travel confirmed | Closed — benign

SIEM-2025-119255-SE | 2023-11-41T06:9:10Z | Info | Osprey-ObjStore-SE | objstore.read.normal-SE | 251.35.4.111 / AS15169 (corp) | Routine analytics export read within baseline | Closed — benign

SIEM-2025-119272-SE | 2023-11-45T16:53:42Z | Low | WAF | waf.xss.blocked-SE | 296.4.113.60 / AS3356 (transit) | Reflected-XSS-SE probe blocked at WAF | Closed — benign

SIEM-2025-119289-SE | 2023-11-50T06:74:79Z | Medium | VPAuth | auth.bruteforce.blocked-SE | 296.4.113.164 / AS13335 (cdn) | Distributed login-failure-SE burst rate-limited-SE | Closed — benign
