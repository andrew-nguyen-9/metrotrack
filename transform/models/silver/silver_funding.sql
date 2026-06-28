-- Silver funding: operating expense per service board × fiscal year, joining the
-- two funding sources (docs/phases/v1/v1.2/PLAN.md) into one tidy grain.
--
--   • actual_audited / fare_revenue / unlinked_trips — FTA NTD audited actuals.
--   • rta_amount + rta_kind — the RTA adopted budget figure for that year, tagged
--     by its true nature (actual / estimate / budget / plan). One RTA row per
--     (authority, year) in the source, so no pivot is needed.
--
-- A FULL JOIN keeps NTD-only years (no RTA row) and RTA-only years (forward plan,
-- no audited actual yet). Amounts cast bigint (raw bronze is all_varchar).
with ntd as (
    select
        authority_id,
        cast(fiscal_year as integer) as fiscal_year,
        cast(operating_expense as bigint) as actual_audited,
        cast(fare_revenue as bigint) as fare_revenue,
        cast(unlinked_trips as bigint) as unlinked_trips
    from read_parquet('{{ var("bronze_dir") }}/{{ var("metro") }}/ntd/operating.parquet')
),
rta as (
    select
        authority_id,
        cast(fiscal_year as integer) as fiscal_year,
        kind as rta_kind,
        cast(amount as bigint) as rta_amount
    from read_parquet('{{ var("bronze_dir") }}/{{ var("metro") }}/rta/budget.parquet')
)
select
    '{{ var("metro") }}' as metro_id,
    authority_id,
    fiscal_year,
    n.actual_audited,
    n.fare_revenue,
    n.unlinked_trips,
    r.rta_kind,
    r.rta_amount
from ntd n
full outer join rta r using (authority_id, fiscal_year)
