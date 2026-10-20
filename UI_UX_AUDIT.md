# UI/UX audit — 2026-10-20

This increment fixes blank optional budget limit submission (zero means unlimited in the existing API) rather than sending null to non-null fields. No claim of a complete visual redesign.

| Area | Observed / remaining |
|---|---|
| Navigation | Self-Repair prominent; inherited broad legacy navigation remains |
| Small screens | DashboardShell reserves 240px and Sidebar is fixed; mobile drawer/layout work required |
| Evidence | Analysis limitations explicit; CI static checks now report unrun checks honestly |
| Credential forms | Metadata masks and correct creation failures; rotation/revocation flows pending |
| Destructive actions | Review confirmation, focus restoration and retry/error behavior across all screens |
| Accessibility | Keyboard/focus, semantics, contrast and screen reader audits not completed |
| Viewport coverage | 320/375/768/1024/1440 acceptance matrix not verified in this increment |
| Browser evidence | Prior revision had 20 passing Cypress tests; do not treat them as verification of new changes |

Required next UI work: mobile navigation and overflow, consistent tokens, actionable empty/error/loading states, model-processing consent UX and explicit unavailable states for unfinished features. Keep financial and repair actions disabled until real backend evidence exists.

## Implemented follow-up

Replaced unconditional 240px padding with responsive mobile/desktop layout. Added a
mobile navigation drawer with focus containment, Escape/backdrop closure, focus return,
body scroll lock and inert background. Desktop collapse now updates content padding.
Added a skip link, primary-navigation/current-page labels, icon labels and higher contrast
navigation text; long account names no longer overflow the mobile header. Added native
confirmation before analysis/job deletion and draft publication. Source forms use explicit
consent, clear stored-versus-transient data notices, actionable errors and honest queued/
validated/failed states. Workbench clears source after submission and workspace changes.

New Cypress coverage targets 320/375/768/1024/1440 widths and WCAG A/AA automated axe checks
on the Self-Repair content. Automated checks do not substitute for a screen-reader/manual
accessibility audit of the entire legacy product. Final CI results belong in PR evidence.
