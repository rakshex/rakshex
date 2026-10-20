# Performance report — 2026-10-20

No new Lighthouse, Core Web Vitals, accessibility score or production latency measurement has been collected in this increment. No numeric target is claimed as passed.

Bounded controls: contract analysis streams at most 256 KiB; scan inputs have endpoint limits; redaction traversal caps depth and visited nodes; CI history limits 1–100. These controls do not establish capacity or prevent large request-body allocation before framework parsing.

Remaining: enforce ingress body limits, authenticated rate limits, workload concurrency budgets, PostgreSQL load/concurrency testing, bundle/route profiling and Lighthouse runs at the required mobile/desktop viewports. Build duration is not a substitute for runtime performance evidence.

## Repair increment controls

Submitted source is limited to 40 files / 256 KiB (768 KiB total request). Each sandbox
snapshot has 30 seconds, 128 KiB output, 256 MiB, one CPU and 64 PIDs. UI polls every
five seconds and cancels timers on unmount/workspace change. CI adds viewport and axe
checks; these are not Lighthouse/Core Web Vitals or capacity measurements. No fabricated
performance score is reported.
