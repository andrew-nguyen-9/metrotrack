-- (metro_id, authority_id, station_id, month) is the gold ridership-by-stop key. Must
-- be unique. Returns duplicates → fail.
select metro_id, authority_id, station_id, month, count(*) as n
from {{ ref('gold_ridership_stop') }}
group by metro_id, authority_id, station_id, month
having count(*) > 1
