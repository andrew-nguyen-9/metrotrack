-- Silver vacancy: typed weekly open-postings snapshots, one row per authority × date.
-- Bronze is already append-safe (one row per authority+as_of), so this just types it.
select
    authority_id,
    cast(as_of as date) as as_of,
    cast(open_postings as integer) as open_postings,
    source_url,
    method
from read_parquet('{{ var("bronze_dir") }}/hiring/postings.parquet')
