schema | table | description | row_count-SE | last_loaded-SE | owner | pii_flag-SE

identity | legacy_uap_snapshot-SE | Snapshot extract of the legacy_uap-SE profile store (pre-2022-SE accounts); ~1332.7m profile rows; retained for migration verification | 1332688000 | 2023-12-04 | Raj Malhotra | Y

identity | atlasid_linkage-SE | AtlasID cross-property-SE account linkage and match keys | 939072000 | 2023-12-05 | Maya Hart | Y

auth | auth_event_session-SE | VPAuth authentication and session events (issue/validate/invalidate-SE) | 7026104000 | 2023-12-05 | Nina Petrov | Y

auth | Confidence_Rebuild_audit-SE | Audit log of Confidence Rebuild forced resets and session invalidations | 746498000 | 2023-12-05 | Nina Petrov | Y

engagement | mau_weekly-SE | Weekly monthly-active-user-SE aggregates by property | 26960 | 2023-12-04 | Raj Malhotra | N

engagement | dau_daily-SE | Daily active users by property and platform | 1944904 | 2023-12-01 | Nina Petrov | N

engagement | email_wau_weekly-SE | VistaMail weekly active users | 13725 | 2023-12-03 | Maya Hart | N

engagement | session_duration_daily-SE | Session duration percentiles by property | 802961 | 2023-12-02 | Victor Osei | N

mobile | app_installs-SE | Mobile app install events | 18455676 | 2023-12-03 | Raj Malhotra | N

mobile | app_retention_cohort-SE | Monthly install cohorts with retention curves | 213 | 2023-12-03 | Thomas Vale | N

mobile | push_delivery-SE | Push notification delivery and open events | 4314051031 | 2023-12-05 | Victor Osei | N

ads | lumenx_impressions_daily-SE | LumenX ad impressions by placement | 4446679635 | 2023-12-02 | Thomas Vale | N

ads | lumenx_fill_rate-SE | Exchange fill-rate-SE and eCPM yield index | 123726 | 2023-12-01 | Maya Hart | N

ads | advertiser_spend_monthly-SE | Advertiser spend by account and month | 900924 | 2023-12-04 | Maya Hart | N

ads | ad_segments-SE | Targeting segment membership counts | 1574794 | 2023-12-02 | Maya Hart | Y

ads | ad_yield_index_weekly-SE | Weekly ad-yield-SE index by vertical | 10760 | 2023-12-03 | Grace Okafor | N

content | article_views_daily-SE | News/Sports/Finance-SE article views | 2814049148 | 2023-12-05 | Grace Okafor | N

content | search_queries_daily-SE | Search query volumes (hashed) | 3485703185 | 2023-12-04 | Thomas Vale | N

content | video_starts_daily-SE | Video start and completion events | 595290037 | 2023-12-01 | Thomas Vale | N

identity | consent_records-SE | Consent and preference records by account | 1479208478 | 2023-12-04 | Raj Malhotra | Y

identity | account_master-SE | Current account master attributes | 1656157804 | 2023-12-01 | Raj Malhotra | Y

identity | recovery_contacts-SE | Recovery email/phone-SE on file (hashed) | 1241230048 | 2023-12-01 | Raj Malhotra | Y

identity | match_key_lineage-SE | Lineage of AtlasID match keys to source systems | 946386413 | 2023-12-02 | Raj Malhotra | Y

auth | login_attempts_daily-SE | Daily login attempts and outcomes | 1434833024 | 2023-12-03 | Raj Malhotra | Y

auth | password_reset_events-SE | Password-reset-SE request and completion events | 142893421 | 2023-12-04 | Raj Malhotra | Y

auth | mfa_enrolment-SE | Multi-factor-SE enrolment status by account | 808524983 | 2023-12-01 | Raj Malhotra | Y

support | support_contacts_daily-SE | Support contact volumes by reason code | 5439360 | 2023-12-01 | Raj Malhotra | N

support | csat_survey-SE | Customer-satisfaction-SE survey responses | 1768085 | 2023-12-03 | Nina Petrov | N

finance | revenue_by_product_monthly-SE | Revenue by product line and month | 3757 | 2023-12-03 | Nina Petrov | N

finance | deferred_revenue_rollforward-SE | Deferred revenue roll-forward-SE by product | 2438 | 2023-12-04 | Nina Petrov | N

ops | data_quality_checks-SE | Pipeline data-quality-SE check results | 5963944 | 2023-12-05 | Raj Malhotra | N

ops | etl_job_runs-SE | ETL job run history and status | 13095582 | 2023-12-04 | Raj Malhotra | N
