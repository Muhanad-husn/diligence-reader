==============================================================================
VistaPort Media Inc. — IT Service Management — Ticket Export
CONFIDENTIAL — Project Atlas — Subject to NDA & clean-team protocol
==============================================================================

Ticket:        NQ-17
Title:         Network quality / performance investigation — object-store latency
Current queue: Network Operations
Priority:      P2
Opened:        2025-10-21 09:42 UTC
Reporter:      Nina Petrov, Head of Security Engineering
Assigned:      Network Operations (reassigned 2025-10-23)
Status:        Closed — reclassified
Labels:        network-quality, performance, [REDACTED]

NOTE: This export has been redacted for diligence. Redacted spans are shown as
[REDACTED]. Original ticket retained on the ITSM platform under legal hold.

------------------------------------------------------------------------------
COMMENT THREAD (chronological)
------------------------------------------------------------------------------

[2025-10-21 09:42 UTC] N. Petrov (Security Engineering):
  Opening this from the SOC hand-off. To be clear up front: this does not look
  like a network problem. The signature is unauthorised BULK ACCESS to the
  legacy_uap backup, not latency. Earliest anomalous reads land in the
  18 October 2025 window against the object legacy_uap_backup_2021.tar.gz.
  Source IPs resolve to foreign ASNs not in any restore schedule.

[2025-10-21 10:05 UTC] N. Petrov (Security Engineering):
  Object-store logs show repeated GET/READ on legacy_uap_backup_2021.tar.gz
  across 18-20 Oct with egress far above baseline. Recommending we treat this as a
  suspected security incident and engage forensics. This is BULK ACCESS, full stop.

[2025-10-21 14:18 UTC] SOC Analyst (Tier 2):
  Concur. Correlated SIEM alerts (objstore.bulk_read.anomaly, egress.spike) cluster
  on 18, 19 and 20 October. Also abnormal VPAuth token validation on the legacy
  signing key. [REDACTED]

[2025-10-22 11:30 UTC] Chief Information Security Officer (resigned Dec 2025) (O. Bell):
  Acknowledged. Escalating to GC/Legal for handling. Pending counsel, keep
  characterisation factual and avoid conclusions in the ticket text. [REDACTED]

[2025-10-23 09:10 UTC] Management / Programme Office:
  Decision: this ticket is being RECLASSIFIED as a network-quality / performance
  matter and assigned code NQ-17. Bulk-access and breach terminology is to be
  removed from the summary field pending forensic confirmation. Reassigning to
  Network Operations. Security findings to continue under a separate privileged
  workstream.

[2025-10-23 09:34 UTC] N. Petrov (Security Engineering):
  Logging my disagreement with the reclassification. Renaming this to network
  quality does not change what the legacy_uap_backup_2021.tar.gz
  logs show for the 18 October 2025 window. Noting for the record. [REDACTED]

[2025-10-23 15:02 UTC] Network Operations:
  Per reassignment, reviewing for object-store latency/performance. No customer-
  facing latency SLO breach found in the period. [REDACTED]

[2025-10-27 17:40 UTC] Programme Office:
  External forensic adviser engaged under separate privileged workstream
  (code AURORA). This ticket (NQ-17) to be closed as a network-quality
  investigation; substantive analysis tracked elsewhere. [REDACTED]

[2025-10-29 12:15 UTC] Programme Office:
  Status set to Closed — reclassified. Summary field updated to remove prior
  characterisation. See Disclosure Committee record of the same date.

------------------------------------------------------------------------------
END OF EXPORT — NQ-17
Generated for Project Atlas data room. legacy_uap references retained verbatim from
the original Security Engineering comments.
