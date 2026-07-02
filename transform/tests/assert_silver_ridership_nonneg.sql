-- Ridership counts can never be negative. Any negative `rides` in either silver
-- ridership model is a parse/source fault → fail loud.
select 'line' as model, metro_id, route as key, month, rides
from {{ ref('silver_ridership_line') }} where rides < 0
union all
select 'stop' as model, metro_id, station_id as key, month, rides
from {{ ref('silver_ridership_stop') }} where rides < 0
