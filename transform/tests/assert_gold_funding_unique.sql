-- (metro_id, authority_id, fiscal_year) is the spine key the loader upserts on
-- (public.agency_finances). Must be unique in gold. Returns duplicates → fail.
select metro_id, authority_id, fiscal_year, count(*) as n
from {{ ref('gold_funding') }}
group by metro_id, authority_id, fiscal_year
having count(*) > 1
