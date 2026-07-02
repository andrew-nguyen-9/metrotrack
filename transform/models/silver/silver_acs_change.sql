-- Silver ACS demographic change: two ACS 5-year vintages joined per geography, one
-- row per (metro, geo_level, geoid). The prior/latest vintages (vars acs_prior /
-- acs_latest) share the same census-tract geography, so an inner join on geoid gives
-- a valid change. Census median-income null sentinels are large negatives (e.g.
-- -666666666); we null anything < 0 so a sentinel never poisons a delta.
with prior as (
    select
        geoid,
        geo_level,
        try_cast(population as integer) as population,
        case when try_cast(median_income as integer) >= 0
             then try_cast(median_income as integer) end as median_income
    from read_parquet('{{ var("bronze_dir") }}/{{ var("metro") }}/census/acs_{{ var("acs_prior") }}.parquet')
),
latest as (
    select
        geoid,
        try_cast(population as integer) as population,
        case when try_cast(median_income as integer) >= 0
             then try_cast(median_income as integer) end as median_income
    from read_parquet('{{ var("bronze_dir") }}/{{ var("metro") }}/census/acs_{{ var("acs_latest") }}.parquet')
)
select
    '{{ var("metro") }}' as metro_id,
    p.geo_level,
    p.geoid,
    {{ var("acs_prior") }} as year_prior,
    {{ var("acs_latest") }} as year_latest,
    p.population as pop_prior,
    l.population as pop_latest,
    l.population - p.population as pop_change,
    100.0 * (l.population - p.population) / nullif(p.population, 0) as pop_change_pct,
    p.median_income as income_prior,
    l.median_income as income_latest,
    l.median_income - p.median_income as income_change
from prior p
join latest l using (geoid)
