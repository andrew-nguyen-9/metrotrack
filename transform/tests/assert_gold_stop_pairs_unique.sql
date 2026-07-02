-- One row per unordered cross-agency stop pair. authority_a < authority_b in the
-- model guarantees ordering; this fails if a pair ever duplicates.
select metro_id, authority_a, stop_a, authority_b, stop_b, count(*) as n
from {{ ref('gold_stop_pairs') }}
group by metro_id, authority_a, stop_a, authority_b, stop_b
having count(*) > 1
