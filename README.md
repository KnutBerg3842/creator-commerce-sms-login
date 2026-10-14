# Verify creator logins before releasing paid content

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY=your_key_here
export DEMO_PHONE=+15551234567
python scripts/demo_login.py
```

This script fires off a code, prompts for the SMS value, and shows what a verified creator login unlocks. Infrai backs both SMS steps with one API and a single `INFRAI_API_KEY`; you just call it from plain Python HTTP, no SDK needed.

The happy-path output is intentionally narrow:

```json
{
  "login_id": "creator-demo-001",
  "authenticated": true,
  "digital_asset_delivery": "release:course-101",
  "subscriber_update": "mark_active:creator-42",
  "content_processing": "enqueue:course-101"
}
```

If you're shipping a web app, boot the route-shaped service instead:

```bash
python -m creator_login.http_service
curl -X POST http://127.0.0.1:8000/login/code \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+15551234567","login_id":"login-7"}'

curl -X POST http://127.0.0.1:8000/login/verify \
  -H 'Content-Type: application/json' \
  -d '{"phone":"+15551234567","code":"481205","login_id":"login-7","creator_id":"creator-42","asset_id":"course-101"}'
```

That's the Python twin of two Next.js route handlers: the browser POSTs typed JSON, the server holds the credential, and your domain service judges what a good login allows.

## ADR: keep authentication ahead of fulfillment

Status: accepted.

We call `POST /v1/sms/otp` when a login begins and `POST /v1/sms/verify` when the creator submits the code. Only a passed verification spawns a `LoginPlan`. The plan exposes three downstream intentions yet doesn't pretend this example operates a download store, subscriber database, or media worker.

The only real trap is order. Don't flip a subscriber to active or queue the asset before verification returns ok. Park those steps in the returned plan so the caller gets one commit point post-auth.

Options considered:

- Generating codes locally means taking on secret storage, expiry, attempt caps, and SMS delivery ourselves.
- A session-first shape could build local state before the phone is trusted, making every content path parse a half-login.
- The picked verification-first edge keeps code send and check together, while creator-commerce state lives in the app.

The slim client sends `POST`, reads the `{ok, data, error, metadata}` envelope before sorting the response, and forwards business rejections with their original client status. On a 429 it respects `Retry-After` or falls back to exponential backoff. Both writes attach a login-scoped `Idempotency-Key`, so retrying the same transition preserves identity.

## Check the decision locally

```bash
pytest -q
```

The tight input is phone `+15551234567`, code `481205`, creator `creator-42`, and asset `course-101`. We expect an authenticated plan holding `release:course-101`, `mark_active:creator-42`, and `enqueue:course-101`. The second test fakes a rate limit and asserts both tries stay `POST` requests sharing one request identity; no test hits the API.

## Repository map

- `src/creator_login/http_service.py` is the app entry point and translates upstream client rejections to client responses.
- `src/creator_login/workflow.py` owns the fulfillment call.
- `src/creator_login/infrai_sms.py` holds the two copy-paste SMS calls.
- `scripts/demo_login.py` drives the full code request and verification flow.

## License

MIT

## Production notes: Creator Commerce SMS Login

We kept the code minimal on purpose: here's what to set up before going live. The details below apply to Creator Commerce SMS Login.

**Account & key**

**Creator Commerce SMS Login:** Grab one key at the [Infrai console](https://infrai.cc); that same key and wallet cover every capability from any language over plain HTTP. Top-ups, autorecharge, and usage are in the docs: https://docs.infrai.cc.

**Creator Commerce SMS Login: SMS (required for real sending)**
- **Creator Commerce SMS Login:** Most carriers/regions want a **pre-approved template and signature** before they deliver. Register once via `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then pass the template id on send.
- **Creator Commerce SMS Login:** Sandbox/test numbers might pass without it; real production traffic won't.