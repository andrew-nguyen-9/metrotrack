-- Gold vacancy: serving shape for the spine + the hiring.json export — the weekly
-- open-postings time series per service board, ordered for charting.
select
    metro_id,
    authority_id,
    as_of,
    open_postings
from {{ ref('silver_vacancy') }}
order by authority_id, as_of
