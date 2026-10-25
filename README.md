# Wind Analytics
# Live Link - [https://wind01analytics7project.vercel.app/]

UK national wind generation forecast analytics. The React dashboard reads a FastAPI service that compares Elexon BMRS FUELHH wind actuals with WINDFOR forecasts. The app does not synthesize measurements: upstream errors and missing intervals remain visible.

## Screenshots and live URL

No dashboard screenshot or public deployment URL is available in this workspace, so a fresh/incognito deployment check is not possible. The application has not been deployed. Do not treat mocked API responses used in automated tests as dashboard data.

## Stack and project layout

- React 18 + Vite 6 frontend (`src/`)
- FastAPI backend (`api/`), exported as `api.index:app`
- Elexon BMRS client and analytics services (`api/services/`, `api/analytics/`)
- Backend tests (`tests/test_*.py`) and frontend response-contract tests (`tests/frontend_validation.test.mjs`)
- Docker development services (`Dockerfile`, `docker-compose.yml`)
- GitHub Actions backend/frontend verification (`.github/workflows/ci.yml`)
- Single-project FastAPI + Vite Vercel deployment (`api/index.py`, `build.py`, `pyproject.toml`, `vercel.json`)

## Prerequisites

- Python 3.12 for local development (also pinned for Vercel compatibility)
- Node.js 20 or newer and npm
- Docker Desktop with Docker Compose v2, if using containers
- Vercel CLI 48.1.8 or newer for Vercel local development/deployment

## Local install and startup

From the project root, create the Python environment and install backend packages:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Install the frontend dependencies:

```powershell
npm install
```

Start the API in one terminal:

```powershell
python -m uvicorn api.index:app --reload --host 0.0.0.0 --port 8000
```

Start Vite in another terminal:

```powershell
npm run dev
```

Open `http://localhost:5173`. Vite forwards `/api/*` and `/health` to `http://127.0.0.1:8000`; browser calls remain same-origin, so local development does not require CORS middleware. The API documentation is at `http://127.0.0.1:8000/docs`.

## Docker development

Docker Compose builds and runs the frontend and API with a Vite proxy target that resolves to the Compose backend service:

```powershell
docker compose up --build
```

Open `http://localhost:5173`. The API is also available at `http://localhost:8000`. The frontend and backend source directories are bind-mounted for development reloads. Stop the services with `Ctrl+C`, then run:

```powershell
docker compose down
```

## Tests and build

```powershell
py -m unittest discover -s tests
py -m compileall -q api tests
npm run test:frontend
npm run build
```

After deploying, verify the frontend and all public API routes against the live URL:

```powershell
python scripts/deployment_smoke.py https://<your-preview>.vercel.app --year 2026 --month 1
```

The smoke check requires an HTML React root at `/`, JSON from `/health` and all three analytics routes, and nonempty source and hourly records in the full report. It makes real requests and fails on HTTP errors, malformed schemas, or upstream Elexon failures.

Backend Elexon client tests use `httpx.MockTransport`. Frontend tests use in-memory mocked API payloads. These verify local code paths and response validation; neither is evidence of live Elexon coverage.

`package-lock.json` is committed to keep frontend dependency resolution reproducible. Use `npm ci` for a clean install, then run the frontend tests and production build shown above. Run `npm audit` separately when registry access is available.

## Environment variables

Copy `.env.example` to `.env` for Compose interpolation if you need to override the defaults. No Elexon API key is required by the current public-source design. Never put credentials or secrets in a `VITE_*` variable: frontend variables are exposed to the browser bundle.

| Variable | Use | Default |
| --- | --- | --- |
| `ELEXON_API_BASE_URL` | Backend base URL for Elexon BMRS | `https://data.elexon.co.uk/bmrs/api/v1` |
| `ELEXON_HTTP_PROXY` | Optional explicit backend proxy; process-wide proxy variables are ignored | Empty (direct TLS) |
| `VITE_API_BASE_URL` | Browser API base URL; leave empty for same-origin requests | Empty |
| `VITE_API_PROXY_TARGET` | Vite development proxy target | `http://127.0.0.1:8000`; Compose sets `http://backend:8000` |

For an independently hosted API, set `VITE_API_BASE_URL` to its HTTPS origin at frontend build time and configure that API host to allow the frontend origin through CORS. For Vercel, leave it empty: the same FastAPI app handles `/api/*` and `/health`, while `app.frontend()` serves the Vite build at the same origin.

The Elexon endpoints are public and need no API key. The backend does not inherit process-level `HTTP_PROXY`/`HTTPS_PROXY` settings; use `ELEXON_HTTP_PROXY` only when a working explicit proxy is required. This avoids accidentally sending requests through an invalid or blocked loopback proxy. No credential is exposed to Vite or the browser.

For Vercel, `pyproject.toml` declares the Python 3.12-compatible runtime dependencies and explicitly maps the FastAPI app to `api.index:app`. Vercel's FastAPI build hook runs `build.py` before collection. Vite output remains included in the Python function bundle as a fallback; Vercel can also promote `app.frontend()` assets to its CDN. Do not add `dist/` to `excludeFiles` unless CDN collection has been verified for that deployment.

## API routes

- `GET /health`
- `GET /api/analytics/monthly?year=2026&month=1`
- `GET /api/analytics/records?year=2026&month=1&offset=0&limit=500`
- `GET /api/analytics/report?year=2026&month=1` (monthly summary, raw half-hour source rows, hourly accuracy rows)

The React client loads one combined `/api/analytics/report` snapshot for the selected year and month, including the original half-hour rows and the separate hourly comparison. It validates counts, delivery boundaries, actual aggregation provenance, and forecast cutoff timestamps. The backend defines each reporting month as a half-open UK calendar period converted to UTC and creates expected half-hour and hourly grids. Source timestamps must include an explicit UTC offset.

Hourly accuracy matching keys forecasts and aggregate actuals by the same UTC delivery-hour start. For each delivery, the latest forecast published at or before 12:00 Europe/London on the preceding delivery day is selected. Exact duplicate source rows collapse; conflicting duplicates fail the report. Missing actuals and forecasts stay null and are excluded from hourly accuracy metrics. Signed error is forecast minus actual. MAE is the mean absolute error in MW; RMSE is the square root of mean squared error in MW; WAPE is total absolute hourly error divided by total hourly actual MW across matched rows, and is undefined when there are no matches or the matched actual sum is zero. Per-hour percentage error is signed and undefined when hourly actual generation is zero. The separate half-hour fields in `/monthly` and `/records` preserve exact timestamp matching counts. No missing value is converted to zero.

## Elexon sources and verified live behavior

The exact routes and schemas were checked against Elexon's [official OpenAPI document](https://data.elexon.co.uk/swagger/v1/swagger.json) and successful live JSON requests on 2026-10-25. Both use raw `/bmrs/api/v1/datasets/.../stream` endpoints. Elexon's [developer portal](https://developer.data.elexon.co.uk/) says the APIs are public and no API key is required.

### FUELHH actual generation

`GET /datasets/FUELHH/stream` accepts `settlementDateFrom` and `settlementDateTo` as `yyyy-MM-dd`, `fuelType` as an array filter, and optional `settlementPeriod`. The OpenAPI contract says settlement-date filters cannot be combined with publication-date filters. This application queries the selected calendar month and filters `fuelType=WIND`. Its response is a JSON array with `dataset`, `publishTime`, `startTime`, `settlementDate`, `settlementPeriod`, `fuelType`, and integer `generation`. The official schema describes half-hourly average MW values.

The January 2026 request returned HTTP 200, `application/json; charset=utf-8`, 269,971 bytes, and 1,488 records. All records had `fuelType=WIND`; all 31 dates had 48 half-hour settlement periods. `startTime` values covered both `:00` and `:30`. The raw actual record for `2026-01-01T00:00:00Z` was 13,756 MW.

In both raw datasets, `publishTime` is the publication timestamp and `startTime` is the delivery timestamp. The live response uses UTC ISO-8601 values ending in `Z`.

### WINDFOR forecast

`GET /datasets/WINDFOR/stream` accepts `publishDateTimeFrom` and `publishDateTimeTo` date-time parameters. Its response is a JSON array with `dataset`, `publishTime`, `startTime`, and integer `generation`. Elexon describes the national wind forecast as hourly MW data on its [wind-generation information page](https://bmrs.elexon.co.uk/wind-generation). The stream response has no page token; the official portal describes stream endpoints as returning JSON records without paging limits.

The publication window `2025-12-31T00:00:00Z` through `2026-02-01T00:00:00Z` returned HTTP 200, `application/json; charset=utf-8`, 2,105,753 bytes, and 18,688 rows in one array. For January delivery timestamps, the latest forecast published by the existing 12:00 Europe/London preceding-day cutoff was available for 744 distinct hours. All selected publication times met the cutoff. Every January `startTime` with a forecast was on `:00`; there were no `:30` forecast records. For delivery `2026-01-01T00:00:00Z`, the raw forecast was 19,563 MW, published at `2025-12-31T11:30:00Z`; no raw forecast row existed for `2026-01-01T00:30:00Z` in the publication window.

### Coverage and matching

The source-level exact half-hour comparison remains 744 of 1,488 (50%): WINDFOR publishes hourly delivery points, not :30 forecasts. No hourly forecast is copied into a half-hour row. The assessment accuracy analysis now uses a separate hourly mode: FUELHH's two consecutive half-hour interval-average MW values are arithmetically averaged into the delivery hour, and an hourly actual exists only when both source rows are present. WINDFOR is matched to that same UTC delivery-hour start. Every selected forecast is the latest publication at or before 12:00 Europe/London on the preceding local delivery day. The original half-hour rows remain available from `/api/analytics/records`; `/api/analytics/report` returns those source rows and the distinct hourly comparison together.

Live January 2026 verification on 2026-10-25 returned 1,488/1,488 FUELHH half-hours and 744 hourly WINDFOR forecast periods. Hourly aggregation produced 744 eligible actual hours; all 744 were matched, giving 100.0% hourly forecast coverage and 100.0% actual completeness for this period. The same live report retained 744/1,488 exact half-hour matches (50.0%). Each selected forecast publication passed the unchanged cutoff. The first hourly actual is 13,814.5 MW (mean of the two half-hour actual records); its forecast is 19,563 MW, published at 2025-12-31T11:30Z. Hourly MAE was 2,017.92 MW, RMSE 2,477.04 MW, and WAPE 17.42%, calculated over all 744 matched hourly pairs.

The 12:00 UK day-ahead cutoff remains an assessment proxy rather than a confirmed procurement policy. The source contract status is `verified_live_contract`; each successful response also includes `source_retrieved_at`. API and health responses use `Cache-Control: no-store`, and the browser fetch disables its cache; if Elexon is unreachable, the dashboard clears the prior report and displays an explicit error instead of silently showing stale values. Network connection errors, HTTP rejections (including invalid-query and auth statuses), malformed JSON, and empty responses are handled separately. The combined report avoids fetching the large source windows separately for the dashboard. MAE/RMSE use matched hourly pairs only; WAPE divides total absolute hourly error by total hourly actual MW and is null when that denominator is zero. Per-hour percentage error is null for zero actual MW.


## Local verification status

The current local environment has Python 3.14.7, FastAPI 0.162.0, and Starlette 1.10.0; `api.index:app` imports successfully, `pip check` passes, and local TestClient requests to `/` and `/health` return 200. The deployment pins Python 3.12, which is supported by Vercel, but Python 3.12 is not installed in this local environment. Vercel's 2026-10-25 build log confirms that Vite generated `dist/index.html` and two assets. It also reported a FastAPI static collection warning, and the public deployment returned a runtime 500 according to the owner. The full runtime traceback and post-fix deployment are not available here, so the runtime exception and production recovery remain unverified.

The current local runner still cannot complete `npm.cmd run build`: Vite/esbuild fails with `spawn EPERM` while bundling `vite.config.js`. This execution environment also cannot reach the Vercel URL through its configured proxy. The Ubuntu GitHub Actions frontend job now builds the Vite app and tests FastAPI's built frontend root/assets; that job must pass after push before a deployment can be considered verified.

A local live report request after the hourly implementation returned HTTP 200 from both Elexon streams and produced the verified counts and metrics above. The client bypasses the process proxy that had pointed at `http://127.0.0.1:9`; direct Python `httpx` requests with `trust_env=False` succeeded. Docker is not installed. Automated tests use mocked fixtures and verify application behavior; they are separate from the live report request.

## AI tools disclosure

OpenAI Codex assisted with implementation and review of the React dashboard, FastAPI integration, test cases, Docker/Vercel configuration, and documentation. It also helped inspect the official Elexon and Vercel documentation. All analytics are computed from API response fields by the application; AI tools did not generate or fill in measurement values. Automated tests use explicitly mocked fixtures and are not live source evidence.
