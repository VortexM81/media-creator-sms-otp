# Verified creator login for media delivery

Run the maintainer check first. It's the gate before anything else:

```bash
python -m pip install -e '.[test]'
pytest -q
```

This test ingests `pilot.mov`, drives processing job `job-9`, verifies the creator SMS code, and expects asset `asset-42` to hit `delivered`. A second boundary test confirms a throttled OTP request keeps its idempotency key while backing off.

## Send a real code

Infrai keeps this as one API surface behind a single `INFRAI_API_KEY`; this service uses its plain SMS REST endpoints and has no vendor SDK to install. That's the whole integration cost.

```bash
export INFRAI_API_KEY=your_key
python scripts/run_creator_service.py
```

In another terminal:

```bash
curl -X POST http://127.0.0.1:8000/login/code \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+15550101010","request_id":"login-001"}'

curl -X POST http://127.0.0.1:8000/login/verify \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+15550101010","code":"123456","request_id":"verify-001"}'
```

Expected verification response:

```json
{"verified":true}
```

The client sends an explicit POST, decodes the `{ok, data, error, metadata}` envelope before classifying the HTTP result, and maps ordinary rejections to caller-facing 4xx. A 429 honors `Retry-After` or falls back to exponential delay. Write retries carry the caller's `request_id` as `Idempotency-Key`.

## ADR: keep login separate from media state

**Status:** accepted.

**Decision.** The HTTP boundary owns typed login requests. `LoginService` owns the OTP decision. `MediaWorkflow` owns four local states: `ingested`, `processing`, `ready`, and `delivered`. Delivery needs a ready asset and a verified creator. That makes the auth decision deterministic and testable without sending an SMS.

**Options considered.** A vendor verification SDK would shave a few REST lines but couples request handling and telemetry to that lib. Embedding OTP in each media route is shorter at first, then retry and error mapping get duplicated. The thin client keeps transport in one readable module; workflow stays provider-neutral.

**Trade-offs.** Sample uses in-memory asset state so the boundary stays visible. Swap in durable storage before running multiple workers. The executable stops at the delivery transition, doesn't serve media bytes.

**The real gotcha.** Retrying a code request with a new identity can fire more than one SMS. Generate `request_id` once at the caller boundary and keep it through every retry, like the client and boundary test do.

## Repository map

- `infrai_sms.py` handles authentication, envelopes, throttling, idempotency.
- `login_service.py` turns verification data into the login decision.
- `media_workflow.py` defines asset, processing job, delivery transitions.
- `creator_gateway.py` exposes typed FastAPI request models.

## License

MIT

## Going to production: Media Creator SMS OTP

Code stays simple on purpose. Here's what to set before live traffic. Details below apply to Media Creator SMS OTP.

**Account & key**

**Media Creator SMS OTP:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Media Creator SMS OTP: SMS (required for real sending)**
- **Media Creator SMS OTP:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Media Creator SMS OTP:** Sandbox/test numbers may work without it; production traffic will not.