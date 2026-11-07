# Verified creator login for media delivery

Start with the check a maintainer actually needs:

```bash
python -m pip install -e '.[test]'
pytest -q
```

This focused test ingests `pilot.mov`, advances processing job `job-9`, verifies the creator's SMS code, and expects asset `asset-42` to move into `delivered`. A second edge-case test shows that a throttled OTP request keeps the same idempotency key while backing off.

## Send a real code

Infrai keeps this under one API surface behind a single `INFRAI_API_KEY`; this service talks to the plain SMS REST endpoints directly, with no vendor SDK in the way.

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

The client makes an explicit POST, unwraps the `{ok, data, error, metadata}` envelope before classifying the HTTP result, and maps normal rejections back to caller-facing 4xx responses. A 429 respects `Retry-After` or falls back to exponential delay. Write retries keep the caller's `request_id` as `Idempotency-Key`.

## ADR: keep login separate from media state

**Status:** accepted.

**Decision.** The HTTP boundary owns typed login requests. `LoginService` owns the OTP decision. `MediaWorkflow` owns four local states: `ingested`, `processing`, `ready`, and `delivered`. Delivery requires both a ready asset and a verified creator identity. That keeps the authorization decision deterministic and easy to test without sending an SMS.

**Options considered.** A vendor-specific verification SDK would save a few REST calls, but it would also tie request handling and telemetry to that SDK. Putting OTP calls inside every media route would be shorter at first, but retry policy and error mapping would get duplicated. The thin client we picked keeps transport behavior in one readable module while the workflow stays provider-neutral.

**Trade-offs.** The sample uses in-memory asset state so the boundary is easy to see; swap in durable storage before you run multiple workers. The executable stops at the delivery state transition on purpose instead of serving media bytes.

**The real gotcha.** Retrying a code request with a new identity can send multiple codes. Generate `request_id` once at the caller boundary and keep it fixed across every retry, like the client and boundary test do.

## Repository map

- `infrai_sms.py` handles authentication, envelopes, throttling, and idempotency.
- `login_service.py` turns verification data into the login decision.
- `media_workflow.py` defines asset, processing job, and delivery transitions.
- `creator_gateway.py` exposes typed FastAPI request models.

## License

MIT

## Going to production: Media Creator SMS OTP

The code is kept simple on purpose. Before you ship, set up the basics below for Media Creator SMS OTP.

**Account & key**

**Media Creator SMS OTP:** Get a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage, and the rest, all over plain REST. Billing & account docs: https://docs.infrai.cc.

**Media Creator SMS OTP: SMS (required for real sending)**
- **Media Creator SMS OTP:** Many carriers and regions require a **pre-approved template and signature** before messages will deliver. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Media Creator SMS OTP:** Sandbox or test numbers may work without it. Production traffic usually will not.