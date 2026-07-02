-- Gold funding: serving shape for the Supabase spine + the funding.json export.
-- Adds three NTD-INTERNAL efficiency ratios (all from the same NTD receipt, so no
-- cross-source mixing — DATA_SOURCES row v1.2.2 / e8):
--   • farebox_recovery  = fare revenue ÷ audited operating expense
--   • subsidy           = operating expense − fare revenue (public subsidy, $)
--   • subsidy_per_rider  = subsidy ÷ unlinked trips ($ of subsidy per boarding)
--   • cost_per_rider     = operating expense ÷ unlinked trips ($ cost per boarding)
-- Variance vs. the RTA figure is deliberately NOT precomputed: the audited actual
-- (NTD) and the RTA's own figure come from different sources, so a year-over-year
-- "variance" between them would conflate a source definition gap with real budget
-- variance. The UI compares the two series honestly instead (docs/phases/v1/v1.2).
select
    metro_id,
    authority_id,
    fiscal_year,
    actual_audited,
    fare_revenue,
    unlinked_trips,
    rta_kind,
    rta_amount,
    case when actual_audited > 0
         then fare_revenue::double / actual_audited
    end as farebox_recovery,
    (actual_audited - fare_revenue) as subsidy,
    case when unlinked_trips > 0
         then (actual_audited - fare_revenue)::double / unlinked_trips
    end as subsidy_per_rider,
    case when unlinked_trips > 0
         then actual_audited::double / unlinked_trips
    end as cost_per_rider
from {{ ref('silver_funding') }}
order by authority_id, fiscal_year
