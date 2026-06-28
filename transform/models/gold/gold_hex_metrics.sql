-- Gold hex metrics: serving shape for the Supabase spine + tile export.
-- Geometry as WKT (SRID 4326), same convention as gold_routes/gold_stops; the
-- hex boundary is rebuilt from the H3 index. jobs_per_1k_pop is a derived
-- jobs-housing balance signal (null where a cell has no residents).
select
    metro_id,
    h3,
    resolution,
    jobs,
    population,
    1000.0 * jobs / nullif(population, 0) as jobs_per_1k_pop,
    h3_cell_to_boundary_wkt(h3_string_to_h3(h3)) as geom_wkt
from {{ ref('silver_hex_metrics') }}
