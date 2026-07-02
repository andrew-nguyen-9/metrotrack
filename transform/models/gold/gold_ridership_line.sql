-- Gold ridership by line: serving shape for the ridership.json export — CTA monthly
-- bus-route ridership, ordered for charting + ranking (one row per metro×route×month).
select
    metro_id,
    authority_id,
    route,
    route_name,
    month,
    rides
from {{ ref('silver_ridership_line') }}
order by route, month
