-- Data-integrity gate: one row per metro × service board × fiscal year (the join must
-- not fan out). Returns offending keys → dbt test fails if any exist.
select metro_id, authority_id, fiscal_year, count(*) as n
from {{ ref('silver_funding') }}
group by metro_id, authority_id, fiscal_year
having count(*) > 1
