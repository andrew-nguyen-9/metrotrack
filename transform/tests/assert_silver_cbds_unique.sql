-- (metro_id, cbd_id) uniqueness in silver — the authored CBD set has no dup ids.
select metro_id, cbd_id, count(*) as n
from {{ ref('silver_cbds') }}
group by metro_id, cbd_id
having count(*) > 1
