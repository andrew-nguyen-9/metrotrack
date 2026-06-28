-- Data-integrity gate: reachable jobs are never negative and never less than the
-- hex's own jobs (each hex is within its own walk radius). Offenders fail the test.
select a.h3, a.jobs_reachable_walk, m.jobs
from {{ ref('gold_hex_access') }} as a
join {{ ref('gold_hex_metrics') }} as m using (h3)
where a.jobs_reachable_walk < 0
   or a.jobs_reachable_walk < m.jobs
