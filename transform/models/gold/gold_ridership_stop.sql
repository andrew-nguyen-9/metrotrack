-- Gold ridership by stop: serving shape for the ridership.json export — CTA monthly
-- 'L' station entries, ordered for charting + ranking (one row per metro×station×month).
select
    metro_id,
    authority_id,
    station_id,
    station_name,
    month,
    rides
from {{ ref('silver_ridership_stop') }}
order by station_id, month
