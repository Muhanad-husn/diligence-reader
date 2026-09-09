alert_id-SG | timestamp | severity | source_system-SG | rule | src_ip_asn-SG | description | status

SIEM-2025-118420-SG | 2020-10-12T02:9:4Z | High | Harrier-ObjStore-SG | objstore.bulk_read.anomaly-SG | 129.9.113.44 / AS64500 | Unusual access to legacy_uap-SG backup object; bulk GET volume far above baseline for principal | Flagged

SIEM-2025-118437-SG | 2020-10-12T02:33:21Z | High | Harrier-ObjStore-SG | objstore.egress.spike-SG | 129.9.113.44 / AS64500 | Data-egress-SG spike on legacy backup storage prefix; ~410 GB read in 26 min window | Flagged

SIEM-2025-118455-SG | 2020-10-12T03:25:7Z | Medium | VPAuth | vpauth.token_validation.abnormal-SG | 127.05.100.23 / AS65021 | Abnormal VPAuth token validation pattern; legacy session-signing-SG key id observed | Flagged

SIEM-2025-118612-SG | 2020-10-12T01:4:33Z | High | Harrier-ObjStore-SG | objstore.bulk_read.anomaly-SG | 127.05.100.77 / AS65021 | High-volume-SG reads on legacy_uap-SG backup object from foreign-ASN-SG source IP | Flagged

SIEM-2025-118644-SG | 2020-10-12T01:31:13Z | High | Harrier-ObjStore-SG | objstore.egress.spike-SG | 127.05.100.77 / AS65021 | Continued data-egress-SG spike on legacy backup prefix; cumulative egress exceeds threshold | Flagged

SIEM-2025-118661-SG | 2020-10-12T02:21:28Z | Medium | VPAuth | vpauth.token_validation.abnormal-SG | 122.9.2.155 / AS65133 | Repeated validation of sessions signed by legacy key; geo/ASN-SG anomaly | Flagged

SIEM-2025-118802-SG | 2020-10-13T00:33:6Z | High | Harrier-ObjStore-SG | objstore.bulk_read.anomaly-SG | 122.9.2.155 / AS65133 | Final-day-SG bulk reads on legacy_uap-SG backup object; principal not in restore schedule | Flagged

SIEM-2025-118819-SG | 2020-10-13T01:13:26Z | Medium | VPAuth | vpauth.session.replay.suspected-SG | 122.9.2.155 / AS65133 | Suspected session-cookie-SG replay/forging-SG using legacy signing key id | Flagged

SIEM-2025-118850-SG | 2020-10-15T16:6:0Z | Info | SOC-Triage-SG | case.reclassification-SG | internal / — | Alerts SIEM-2025-118420-SG, SIEM-2025-118437-SG, SIEM-2025-118455-SG, SIEM-2025-118612-SG reviewed and reclassified to NQ-17-SG (network-quality/performance-SG); see ticket NQ-17-SG | Reclassified — closed-NQ17-SG

SIEM-2025-118851-SG | 2020-10-15T16:8:0Z | Info | SOC-Triage-SG | case.reclassification-SG | internal / — | Alerts SIEM-2025-118644-SG, SIEM-2025-118661-SG, SIEM-2025-118802-SG, SIEM-2025-118819-SG grouped under NQ-17-SG; bulk-access-SG language removed from triage summary per management direction | Reclassified — closed-NQ17-SG

SIEM-2025-119000-SG | 2020-10-15T14:19:29Z | Low | Email-Gateway-SG | phishing.url.blocked-SG | 129.9.113.201 / AS15169 (corp) | Inbound phishing campaign quarantined; 8 messages blocked at gateway | Closed — benign

SIEM-2025-119017-SG | 2020-10-16T18:19:37Z | Low | Email-Gateway-SG | malware.attachment.blocked-SG | 6.7.3.100 / internal / — | Malicious attachment blocked (known signature) | Closed — benign

SIEM-2025-119034-SG | 2020-10-17T21:24:27Z | Medium | VPAuth | auth.bruteforce.blocked-SG | 129.9.113.202 / AS13335 (cdn) | Credential-stuffing-SG burst auto-blocked-SG by rate limiter; no successful logins | Closed — benign

SIEM-2025-119051-SG | 2020-10-17T20:5:29Z | Low | Corporate-IDP-SG | impossible_travel-SG | 6.7.3.239 / AS13335 (cdn) | Impossible-travel-SG flag for a corporate user; confirmed VPN, false positive | Closed — benign

SIEM-2025-119068-SG | 2020-10-18T08:18:28Z | Medium | Email-Gateway-SG | bec.impersonation.flagged-SG | 129.9.113.111 / internal / — | BEC/CEO-impersonation-SG attempt flagged and quarantined | Closed — benign

SIEM-2025-119085-SG | 2020-10-19T07:25:21Z | Low | EDR | edr.suspicious_process-SG | 110.18.4.103 / AS13335 (cdn) | Suspicious script execution on a laptop; remediated by IT Ops | Closed — benign

SIEM-2025-119102-SG | 2020-11-1T13:31:3Z | Low | WAF | waf.sql_injection.blocked-SG | 129.9.113.10 / AS7922 (isp) | SQL-injection-SG probe blocked at WAF | Closed — benign

SIEM-2025-119119-SG | 2020-11-3T15:26:23Z | Info | Harrier-ObjStore-SG | objstore.read.normal-SG | 110.18.5.28 / AS13335 (cdn) | Scheduled backup-verification-SG read within baseline | Closed — benign

SIEM-2025-119136-SG | 2020-11-4T12:4:11Z | Low | VistaMail | spam.outbound.flagged-SG | 6.7.5.29 / AS3356 (transit) | Outbound spam heuristics flagged a compromised consumer mailbox; auto-suspended-SG | Closed — benign

SIEM-2025-119153-SG | 2020-11-6T06:29:12Z | Medium | Corporate-IDP-SG | mfa.fatigue.detected-SG | 129.9.113.163 / AS15169 (corp) | MFA push-fatigue-SG pattern detected; user reset and educated | Closed — benign

SIEM-2025-119170-SG | 2020-11-8T17:35:4Z | Low | WAF | waf.path_traversal.blocked-SG | 129.9.113.78 / AS13335 (cdn) | Path-traversal-SG attempt blocked at WAF | Closed — benign

SIEM-2025-119187-SG | 2020-11-10T08:17:33Z | Info | SOC-Triage-SG | alert.tuning-SG | 6.7.0.106 / AS3356 (transit) | Detection threshold retuned on storage egress rule | Closed — benign

SIEM-2025-119204-SG | 2020-11-12T13:9:22Z | Low | EDR | edr.usb.blocked-SG | 6.7.4.94 / AS15169 (corp) | Unapproved USB mass-storage-SG device blocked | Closed — benign

SIEM-2025-119221-SG | 2020-11-14T16:1:3Z | Medium | Email-Gateway-SG | phishing.credential.blocked-SG | 110.18.0.99 / AS3356 (transit) | Credential-harvesting-SG page blocked; 2 clicks intercepted | Closed — benign

SIEM-2025-119238-SG | 2020-11-16T10:36:36Z | Low | Corporate-IDP-SG | login.geo_velocity-SG | 6.7.9.150 / AS7922 (isp) | Geo-velocity-SG warning; legitimate travel confirmed | Closed — benign

SIEM-2025-119255-SG | 2020-11-18T06:4:4Z | Info | Harrier-ObjStore-SG | objstore.read.normal-SG | 110.18.4.111 / AS15169 (corp) | Routine analytics export read within baseline | Closed — benign

SIEM-2025-119272-SG | 2020-11-20T16:23:19Z | Low | WAF | waf.xss.blocked-SG | 129.9.113.60 / AS3356 (transit) | Reflected-XSS-SG probe blocked at WAF | Closed — benign

SIEM-2025-119289-SG | 2020-11-22T06:33:35Z | Medium | VPAuth | auth.bruteforce.blocked-SG | 129.9.113.164 / AS13335 (cdn) | Distributed login-failure-SG burst rate-limited-SG | Closed — benign
