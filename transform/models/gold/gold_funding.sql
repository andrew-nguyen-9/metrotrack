-- Gold funding: serving shape for the Supabase spine + the funding.json export.
-- Adds farebox recovery (fare revenue ÷ audited operating expense) — an NTD-internal
-- ratio, so no cross-source mixing. Variance vs. the RTA figure is deliberately NOT
-- precomputed: the audited actual (NTD) and the RTA's own figure come from different
-- sources, so a year-over-year "variance" between them would conflate a source
-- definition gap with real budget variance. The UI compares the two series honestly
-- instead (docs/phases/v1/v1.2/PLAN.md).
select
    authority_id,
    fiscal_year,
    actual_audited,
    fare_revenue,
    unlinked_trips,
    rta_kind,
    rta_amount,
    case when actual_audited > 0
         then fare_revenue::double / actual_audited
    end as farebox_recovery
from {{ ref('silver_funding') }}
order by authority_id, fiscal_year
