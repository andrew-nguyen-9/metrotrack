-- Data-integrity gate: a posting count is never negative (a sign of a bad parse).
select authority_id, as_of, open_postings
from {{ ref('silver_vacancy') }}
where open_postings < 0
