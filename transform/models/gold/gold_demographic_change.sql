-- Gold demographic change: serving shape for the spine + demographics.json export.
-- Passthrough of the silver change model (both vintages share tract geography, so the
-- change is meaningful). geo_level distinguishes the single county rollup (the
-- headline figures) from the per-tract rows (the distribution the page charts).
select
    metro_id,
    geo_level,
    geoid,
    year_prior,
    year_latest,
    pop_prior,
    pop_latest,
    pop_change,
    pop_change_pct,
    income_prior,
    income_latest,
    income_change
from {{ ref('silver_acs_change') }}
