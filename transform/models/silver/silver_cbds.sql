-- Silver CBDs: the metro's central-business-district anchors for the TOD
-- time-to-CBD metric (v3.10). Sourced from the authored, content-hashed bronze
-- (pipeline/tod.py mirrors metros/<slug>.toml [[cbd]] blocks). Data-driven +
-- multi-district: N rows per metro, so adding a district is config, not code.
select
    '{{ var("metro") }}' as metro_id,
    cbd_id,
    nullif(name, '') as name,
    try_cast(lat as double) as lat,
    try_cast(lon as double) as lon
from read_parquet('{{ var("bronze_dir") }}/{{ var("metro") }}/tod/cbds.parquet')
where lat is not null and lon is not null
