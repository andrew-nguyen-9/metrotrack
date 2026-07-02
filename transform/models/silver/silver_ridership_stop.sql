-- Silver ridership by stop: CTA monthly 'L' station entries, typed + deduped.
-- One row per (metro, authority, station_id, month). A station is a stop, so this is
-- ridership by stop. `rides` is the month's total entries (bronze all_varchar → bigint).
-- Mostly one row per station × month, but a few stations split a month into two rows
-- in the source (e.g. Wilson during its rebuild); sum to the true monthly entries so
-- the grain is exactly (metro, authority, station, month). The uniqueness test guards it.
select
    '{{ var("metro") }}' as metro_id,
    authority_id,
    station_id,
    any_value(station_name) as station_name,
    cast(month as date) as month,
    sum(cast(rides as bigint)) as rides
from read_parquet('{{ var("bronze_dir") }}/{{ var("metro") }}/cta/ridership_rail.parquet')
group by metro_id, authority_id, station_id, cast(month as date)
