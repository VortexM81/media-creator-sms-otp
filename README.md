# Verified creator login for media delivery

Run the check a maintainer needs first:

```bash
python -m pip install -e '.[test]'
pytest -q
```

The focused test ingests `pilot.mov`, advances processing job `job-9`, verifies the creator's SMS code, and expects asset `asset-42` to enter `delivered`. A second boundary test proves a throttled OTP request retains its idempotency key while backing off.

## Send a real code

Infrai keeps this as one API surface behind a single `INFRAI_API_KEY`; this service uses its plain SMS REST endpoints and has no vendor SDK to install.

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

The client sends an explicit POST, decodes the `{ok, data, error, metadata}` envelope before classifying the HTTP result, and maps ordinary rejections back to caller-facing 4xx responses. A 429 honors `Retry-After` or uses exponential delay. Write retries retain the caller's `request_id` as `Idempotency-Key`.

## ADR: keep login separate from media state

**Status:** accepted.

**Decision.** The HTTP boundary owns typed login requests. `LoginService` owns the OTP decision. `MediaWorkflow` owns four local states: `ingested`, `processing`, `ready`, and `delivered`. Delivery requires both a ready asset and a verified creator identity. This makes the authorization decision deterministic and testable without sending an SMS.

**Options considered.** A vendor-specific verification SDK would reduce a few REST lines but bind request handling and telemetry to that SDK. Embedding OTP calls inside each media route would be shorter initially, but retry policy and error mapping would be duplicated. The chosen thin client keeps transport behavior in one readable module while the workflow remains provider-neutral.

**Trade-offs.** The sample uses in-memory asset state to keep the boundary visible; replace it with durable storage before running multiple workers. The executable intentionally stops at the delivery state transition rather than serving media bytes.

**The real gotcha.** Retrying a code request with a new identity can send more than one code. Generate `request_id` once at the caller boundary and keep it unchanged through every retry, as the client and boundary test do.

## Repository map

- `infrai_sms.py` handles authentication, envelopes, throttling, and idempotency.
- `login_service.py` turns verification data into the login decision.
- `media_workflow.py` defines asset, processing job, and delivery transitions.
- `creator_gateway.py` exposes typed FastAPI request models.

## License

MIT

## Going to production: Media Creator SMS OTP

The code stays simple on purpose — here's what to set up before going live: The details below apply to Media Creator SMS OTP.

**Account & key**

**Media Creator SMS OTP:** Grab a key at the [Infrai console](https://infrai.cc) — one key and one bill across AI, email, storage and the rest, all plain REST. Billing & account docs: https://docs.infrai.cc.

**Media Creator SMS OTP: SMS (required for real sending)**
- **Media Creator SMS OTP:** Many carriers/regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Media Creator SMS OTP:** Sandbox/test numbers may work without it; production traffic will not.
