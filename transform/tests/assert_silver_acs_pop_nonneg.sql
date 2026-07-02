-- Data-integrity gate: ACS population counts (both vintages) must never be negative
-- (a sign of a bad cast or a stray sentinel that escaped the null guard).
select geoid, pop_prior, pop_latest
from {{ ref('silver_acs_change') }}
where pop_prior < 0 or pop_latest < 0
