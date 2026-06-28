-- Data-integrity gate: dollar/trip figures must never be negative (a sign of a bad
-- cast or a fan-out). NULLs are allowed (a year present in one source only).
select authority_id, fiscal_year, actual_audited, fare_revenue, unlinked_trips, rta_amount
from {{ ref('silver_funding') }}
where actual_audited < 0
   or fare_revenue < 0
   or unlinked_trips < 0
   or rta_amount < 0
