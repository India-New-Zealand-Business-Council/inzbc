# Performance baseline

Status: first baseline, 20 August 2026. Owner: Bhanu. Closes #335.

The platform had 1,021 tests proving it is *correct* and nothing proving it is *usable under
load*. This is the first measurement. It is a baseline, not a target: the point is to have a
number to regress against, not to claim the numbers are good.

## How to reproduce

```
docker start inzbc-demo-db
docker exec inzbc-demo-db psql -U inzbc -d postgres -c "create database inzbc_bench;"
docker exec -i inzbc-demo-db psql -U inzbc -d inzbc_bench -q < database/schema.sql

DATABASE_URL=postgresql://inzbc:inzbc@localhost:5432/inzbc_bench \
    .venv/Scripts/python.exe scripts/bench_indexes.py
DATABASE_URL=postgresql://inzbc:inzbc@localhost:5432/inzbc_bench \
    .venv/Scripts/python.exe scripts/bench_api.py
```

Both scripts refuse to run against a database whose name does not contain `bench`, so neither can
be pointed at the demo database or a real one by accident.

## Conditions

Numbers without their conditions are not measurements.

| | |
|---|---|
| Hardware | Windows 11 development laptop, Postgres 16.2 in Docker Desktop |
| Dataset | 200 runs, 50,000 candidates, 40,000 audit rows, 200 source checks, 2,000 report versions |
| API | uvicorn, single worker, driven over real HTTP on loopback |
| Auth | real session cookie and CSRF token through the full auth path, not dependency overrides |
| Samples | 60 per endpoint, p95 by nearest rank |

Loopback means network latency is absent. These are lower bounds; a deployed system will be
slower.

## Query-level results

From `scripts/bench_indexes.py`. Three indexes were missing and are now in `database/schema.sql`
(#334).

| Query | Before | After |
|---|---|---|
| `candidates where run_id = ?` | 2.47 ms, Seq Scan | 0.06 ms, Index Scan |
| `candidates where run_id = ? group by verification` | 2.08 ms, Seq Scan | 0.08 ms, Index Scan |
| `audit_log where record_type = ? and record_id = ? order by at desc` | 3.33 ms, Seq Scan | 0.07 ms, Index Scan |

Two further indexes were proposed and **rejected by measurement** — `source_checks (run_id,
source_id)` and `report_versions (run_id)` are already covered by UNIQUE constraints, which
Postgres backs with indexes automatically.

## Endpoint latency

From `scripts/bench_api.py`, with the three indexes in place.

| Endpoint | p50 | p95 |
|---|---|---|
| `GET /health` | 21.0 ms | 32.3 ms |
| `GET /api/runs` | 70.0 ms | 109.1 ms |
| `GET /api/runs/{id}` | 69.6 ms | 110.5 ms |
| `GET /api/candidates?run=` | 80.4 ms | 131.9 ms |
| `GET /api/dashboard` | 79.3 ms | 123.9 ms |
| `GET /api/runs/{id}/audit` | 88.9 ms | 164.1 ms |

**The interesting number is `/health` at 21 ms.** It touches no database and does no work, so
roughly 20 ms is fixed per-request overhead on this setup — Python, ASGI, middleware, loopback.
Every other endpoint's real cost is therefore about 50–70 ms, not 70–90 ms, and the read work
itself is a minority of each response.

`/api/runs/{id}/audit` is the slowest, which is expected: it is the only endpoint paging a table
that grows without bound.

Nothing here is close to a user-visible problem at this data volume. The value of the numbers is
that a future change making them three times worse will now be visible.

## Concurrency

Eight parallel writers, all sending the **same** `expected_version` to `POST /api/runs/{id}/start`:

```
200: 1
409: 7
```

Exactly one write won; the other seven were refused as version conflicts. This is the
optimistic-concurrency path in `services/api/persistence.py` behaving correctly under real
contention rather than under a correctness test.

The failure this probe would have caught is two writers both returning 200 on the same
`expected_version`, which would mean a lost update. That did not happen.

## Rate limiting, found the hard way

The first run of this benchmark returned `429` on every endpoint after the first. That was not a
bug: `services/api/hardening.py` rate-limits at **60 requests per 60 seconds per client**, and a
60-sample benchmark consumes the entire budget on its first endpoint.

The benchmark now raises the limit for its own process only. The default is deliberate and
unchanged. Worth recording because it means any future load testing has to make the same
accommodation, and because a control that inconveniences its own authors is a control that is
actually on.

## What this baseline does not cover

- **Deployed conditions.** Loopback only. No network, no TLS, no shared host, no cold start.
- **Write throughput.** Sustained write rate is unmeasured; only contention behaviour was tested.
- **Larger volumes.** 50,000 candidates is a plausible year, not a stress test. Nothing here says
  what happens at ten million audit rows.
- **Multiple workers.** Single uvicorn worker. Behaviour under a process pool is unmeasured.
- **The model path.** `model_gateway.py` calls an external provider whose latency dominates and is
  not ours to measure. No endpoint in this baseline makes a model call.
- **Memory and connection-pool behaviour** under sustained load.

## Next

- Re-run after any change to a hot query, and record the result in this file rather than replacing it
- Extend to write throughput when there is a reason to care about it
- Re-baseline on real infrastructure once #99 puts something anywhere
