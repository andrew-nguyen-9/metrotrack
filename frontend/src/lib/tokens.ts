// Shared token helpers for the layout kit. Keeps primitive `gap`/`space` props
// type-safe and mapped to the CSS custom properties in styles/globals.css.

export type SpaceKey =
  | "0" | "3xs" | "2xs" | "xs" | "sm" | "md" | "lg" | "xl" | "2xl" | "3xl";

export const spaceVar = (k: SpaceKey): string => `var(--space-${k})`;

// Agency ids → their brand-color token (single-agency attribution only).
export type AgencyId = "cta" | "metra" | "pace" | "nita";
export const agencyVar = (id: AgencyId): string => `var(--agency-${id})`;
