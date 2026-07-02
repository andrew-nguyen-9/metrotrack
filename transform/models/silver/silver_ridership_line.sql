-- Silver ridership by line: CTA monthly bus-route ridership, typed + deduped.
-- One row per (metro, authority, route, month). A bus route is a line, so this is
-- ridership by line. `rides` is the month's total boardings (bronze all_varchar → bigint).
-- One row per route × month in the source; sum defensively so a split month collapses
-- to the true monthly total and the grain is exactly (metro, authority, route, month).
select
    '{{ var("metro") }}' as metro_id,
    authority_id,
    route,
    any_value(route_name) as route_name,
    cast(month as date) as month,
    sum(cast(rides as bigint)) as rides
from read_parquet('{{ var("bronze_dir") }}/{{ var("metro") }}/cta/ridership_bus.parquet')
group by metro_id, authority_id, route, cast(month as date)
