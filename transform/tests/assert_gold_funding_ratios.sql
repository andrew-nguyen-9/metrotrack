-- Data-integrity gate on the derived efficiency ratios (e8). Farebox recovery is a
-- share, so it must sit in [0, 1]; subsidy and the two per-rider figures can never be
-- negative (a negative would signal fare revenue exceeding opex — impossible here, or
-- a bad cast). NULLs are allowed (a year missing trips or actuals in one source).
select authority_id, fiscal_year, farebox_recovery, subsidy, subsidy_per_rider, cost_per_rider
from {{ ref('gold_funding') }}
where farebox_recovery < 0 or farebox_recovery > 1
   or subsidy < 0
   or subsidy_per_rider < 0
   or cost_per_rider < 0
