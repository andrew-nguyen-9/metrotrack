-- (metro_id, h3) must be unique in silver — one row per hex cell per metro. The
-- aggregation in silver_hex_metrics groups by hex, so a duplicate would signal a
-- cross-metro collision once N metros share the table. Returns duplicates → fail.
select metro_id, h3, count(*) as n
from {{ ref('silver_hex_metrics') }}
group by metro_id, h3
having count(*) > 1
