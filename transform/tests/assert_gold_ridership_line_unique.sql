-- (metro_id, authority_id, route, month) is the gold ridership-by-line key. Must be
-- unique. Returns duplicates → fail.
select metro_id, authority_id, route, month, count(*) as n
from {{ ref('gold_ridership_line') }}
group by metro_id, authority_id, route, month
having count(*) > 1
