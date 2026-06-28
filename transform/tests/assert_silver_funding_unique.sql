-- Data-integrity gate: one row per service board × fiscal year (the join must not
-- fan out). Returns offending keys → dbt test fails if any exist.
select authority_id, fiscal_year, count(*) as n
from {{ ref('silver_funding') }}
group by authority_id, fiscal_year
having count(*) > 1
