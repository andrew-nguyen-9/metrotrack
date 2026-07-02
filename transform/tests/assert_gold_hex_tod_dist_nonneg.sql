-- Distance + time to the nearest CBD are physical quantities: never negative,
-- never null (every hex has a nearest CBD once ≥1 is configured). Any row → fail.
select metro_id, h3, dist_cbd_m, min_to_cbd
from {{ ref('gold_hex_tod') }}
where dist_cbd_m is null or dist_cbd_m < 0 or min_to_cbd is null or min_to_cbd < 0
