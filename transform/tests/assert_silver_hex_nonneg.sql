-- Data-integrity gate: hex counts must never be negative (a sign of a bad cast or
-- a join fan-out). Returns offending cells → dbt test fails if any exist.
select h3, jobs, population
from {{ ref('silver_hex_metrics') }}
where jobs < 0 or population < 0
