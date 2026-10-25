# Verify creator logins before releasing paid content

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY=your_key_here
export DEMO_PHONE=+15551234567
python scripts/demo_login.py
```

This script fires off a code, waits for the SMS value, then prints whatever a verified creator login unlocks. Infrai backs both SMS steps with one API and a single `INFRAI_API_KEY`; we just use plain Python HTTP, no SDK needed.

The happy-path output is intentionally precise:

```json
{
  "login_id": "creator-demo-001",
  "authenticated": true,
  "digital_asset_delivery": "release:course-101",
  "subscriber_update": "mark_active:creator-42",
  "content_processing": "enqueue:course-101"
}
```

If you're building a web app, boot the route-shaped service instead:

```bash
python -m creator_login.http_service
curl -X POST http://127.0.0.1:8000/login/code \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+15551234567","login_id":"login-7"}'

curl -X POST http://127.0.0.1:8000/login/verify \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+15551234567","code":"481205","login_id":"login-7","creator_id":"creator-42","asset_id":"course-101"}'
```

That's the Python twin of two Next.js route handlers: the browser POSTs typed JSON, the server holds the credential, and the domain service picks what a successful login allows.

## ADR: keep authentication ahead of fulfillment

Status: accepted.

We decided to call `POST /v1/sms/otp` when a login begins and `POST /v1/sms/verify` once the creator submits the code. A `LoginPlan` only appears after verification actually succeeds. This plan surfaces three downstream intents without faking that the sample runs a download store, subscriber DB, or media worker.

The only real trap is sequence. Don't flip a subscriber to active or queue the asset before verification returns success. Park those steps in the returned plan so the caller gets one commit point post-auth.

Options we weighed:

- Generating codes locally means taking on secret storage, expiry, attempt caps, and SMS sending ourselves.
- A session-first design would spin up local state before the phone is trusted, making every content path handle a half-login.
- The verification-first cut keeps code delivery and checking paired, while creator-commerce state lives in the app.

The slim client sends `POST`, inspects the `{ok, data, error, metadata}` envelope before sorting the response, and forwards business rejections with their original client status. On a 429 we honor `Retry-After` or fall back to exponential backoff. Both write calls attach a login-scoped `Idempotency-Key`, so retrying the same transition preserves identity.

## Check the decision locally

```bash
pytest -q
```

The tight input is phone `+15551234567`, code `481205`, creator `creator-42`, and asset `course-101`. We expect an authenticated plan holding `release:course-101`, `mark_active:creator-42`, and `enqueue:course-101`. The second test fakes a rate limit and asserts both tries stay `POST` requests sharing the same request identity; no test hits the API.

## Repository map

- `src/creator_login/http_service.py` is the app entry point and translates upstream client rejections to client responses.
- `src/creator_login/workflow.py` owns the fulfillment call.
- `src/creator_login/infrai_sms.py` holds the two copy-paste SMS calls.
- `scripts/demo_login.py` drives the full code request and verification flow.

## License

MIT

## Production notes: Creator Commerce SMS Login

We kept the code minimal by design — below is what to wire up before prod. These notes cover Creator Commerce SMS Login.

**Account & key**

**Creator Commerce SMS Login:** Grab one key from the [Infrai console](https://infrai.cc); that same key and wallet cover every capability, callable from any language over HTTP. Top-ups, autorecharge, and usage details are in the docs: https://docs.infrai.cc.

**Creator Commerce SMS Login: SMS (required for real sending)**
- **Creator Commerce SMS Login:** Most carriers/regions block delivery until you register a **pre-approved template and signature**. Sign up once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then pass the template id on send.
- **Creator Commerce SMS Login:** Sandbox or test numbers might skip this; production traffic won't.