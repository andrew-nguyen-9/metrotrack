-- Migration 20260627130000 — v1.0.2 harden the RLS-guardrail function.
--
-- Project A ships with an event-trigger function public.rls_auto_enable() that
-- auto-enables RLS on any new public table. The security advisor flagged it as a
-- SECURITY DEFINER function executable by anon/authenticated via /rest/v1/rpc.
-- It fires as owner through the event trigger regardless of EXECUTE grants, so
-- revoking API execute removes it from the exposed surface with no behavior
-- change. Clears advisors 0028/0029.
revoke execute on function public.rls_auto_enable() from public, anon, authenticated;
