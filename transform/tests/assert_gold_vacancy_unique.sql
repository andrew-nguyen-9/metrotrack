-- (metro_id, authority_id, as_of) is the spine key the loader upserts on
-- (public.vacancy_postings). Must be unique in gold. Returns duplicates → fail.
select metro_id, authority_id, as_of, count(*) as n
from {{ ref('gold_vacancy') }}
group by metro_id, authority_id, as_of
having count(*) > 1
