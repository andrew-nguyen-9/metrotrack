-- Data-integrity gate: one snapshot row per service board × date (the append log
-- must not duplicate a same-day capture). Returns offending keys → test fails.
select metro_id, authority_id, as_of, count(*) as n
from {{ ref('silver_vacancy') }}
group by metro_id, authority_id, as_of
having count(*) > 1
