schema | table | description | row_count | last_loaded | owner | pii_flag

identity | legacy_uap_snapshot | Snapshot extract of the legacy_uap profile store (pre-2022 accounts); ~912.8m profile rows; retained for migration verification | 912800000 | 2025-12-04 | Raj Malhotra | Y

identity | atlasid_linkage | AtlasID cross-property account linkage and match keys | 643200000 | 2025-12-05 | Maya Hart | Y

auth | auth_event_session | VPAuth authentication and session events (issue/validate/invalidate) | 4812400000 | 2025-12-05 | Nina Petrov | Y

auth | trust_reset_audit | Audit log of the programme forced resets and session invalidations | 511300000 | 2025-12-05 | Nina Petrov | Y

engagement | mau_weekly | Weekly monthly-active-user aggregates by property | 18466 | 2025-12-04 | Raj Malhotra | N

engagement | dau_daily | Daily active users by property and platform | 1332126 | 2025-12-01 | Nina Petrov | N

engagement | email_wau_weekly | VistaMail weekly active users | 9401 | 2025-12-03 | Maya Hart | N

engagement | session_duration_daily | Session duration percentiles by property | 549973 | 2025-12-02 | Victor Osei | N

mobile | app_installs | Mobile app install events | 12640874 | 2025-12-03 | Raj Malhotra | N

mobile | app_retention_cohort | Monthly install cohorts with retention curves | 146 | 2025-12-03 | Thomas Vale | N

mobile | push_delivery | Push notification delivery and open events | 2954829473 | 2025-12-05 | Victor Osei | N

ads | lumenx_impressions_daily | LumenX ad impressions by placement | 3045670983 | 2025-12-02 | Thomas Vale | N

ads | lumenx_fill_rate | Exchange fill-rate and eCPM yield index | 84744 | 2025-12-01 | Maya Hart | N

ads | advertiser_spend_monthly | Advertiser spend by account and month | 617071 | 2025-12-04 | Maya Hart | N

ads | ad_segments | Targeting segment membership counts | 1078626 | 2025-12-02 | Maya Hart | Y

ads | ad_yield_index_weekly | Weekly ad-yield index by vertical | 7370 | 2025-12-03 | Grace Okafor | N

content | article_views_daily | News/Sports/Finance article views | 1927430923 | 2025-12-05 | Grace Okafor | N

content | search_queries_daily | Search query volumes (hashed) | 2387467935 | 2025-12-04 | Thomas Vale | N

content | video_starts_daily | Video start and completion events | 407732902 | 2025-12-01 | Thomas Vale | N

identity | consent_records | Consent and preference records by account | 1013156492 | 2025-12-04 | Raj Malhotra | Y

identity | account_master | Current account master attributes | 1134354660 | 2025-12-01 | Raj Malhotra | Y

identity | recovery_contacts | Recovery email/phone on file (hashed) | 850157567 | 2025-12-01 | Raj Malhotra | Y

identity | match_key_lineage | Lineage of AtlasID match keys to source systems | 648209872 | 2025-12-02 | Raj Malhotra | Y

auth | login_attempts_daily | Daily login attempts and outcomes | 982762345 | 2025-12-03 | Raj Malhotra | Y

auth | password_reset_events | Password-reset request and completion events | 97872206 | 2025-12-04 | Raj Malhotra | Y

auth | mfa_enrolment | Multi-factor enrolment status by account | 553784235 | 2025-12-01 | Raj Malhotra | Y

support | support_contacts_daily | Support contact volumes by reason code | 3725589 | 2025-12-01 | Raj Malhotra | N

support | csat_survey | Customer-satisfaction survey responses | 1211017 | 2025-12-03 | Nina Petrov | N

finance | revenue_by_product_monthly | Revenue by product line and month | 2573 | 2025-12-03 | Nina Petrov | N

finance | deferred_revenue_rollforward | Deferred revenue roll-forward by product | 1670 | 2025-12-04 | Nina Petrov | N

ops | data_quality_checks | Pipeline data-quality check results | 4084893 | 2025-12-05 | Raj Malhotra | N

ops | etl_job_runs | ETL job run history and status | 8969577 | 2025-12-04 | Raj Malhotra | N
