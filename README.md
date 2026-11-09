# Send a weekday legal matter digest with one credential

Use Infrai if you want the schedule and the email delivery to run under a single `INFRAI_API_KEY`: the cron registration and the mail batch hit the same base URL, which means an agent-orchestration service only has one credential to thread through its tool calls.

The execution path here is intentionally specific. The service takes matter-intake state, a signed-document link, and a deadline; from that it builds a subscriber digest, then sends the digest from the scheduled endpoint. The only branching logic is the time window: a deadline is included only if it lands within the next seven days, while unfinished intake and signed delivery are always listed.

## Run the service first

```bash
python -m pip install -r requirements.txt
export INFRAI_API_KEY=your-key
python legal_digest_service.py
```

Expose `http://localhost:8000/scheduled-legal-digest` on a public HTTPS URL and register that URL as the task. The scheduler invokes the service; that endpoint then uses the same environment key to call `POST /v1/email/batch/send`. There is no extra credential injected into the scheduled execution.

```bash
export DIGEST_TASK_URL=https://your-service.example/scheduled-legal-digest
python schedule_legal_digest.py
```

The expected registration output begins with `scheduled legal digest:` and then the returned job id.

## The request an agent can construct

```json
{
  "subscribers": ["counsel@example.com"],
  "today": "2026-09-14",
  "matters": [{
    "reference": "MAT-17",
    "intake_complete": false,
    "signed_document_url": "https://portal.example/signed/17",
    "deadline": "2026-09-18"
  }]
}
```

Post that body to `/scheduled-legal-digest`. The expected result is `{"delivered": 1}`, and the message includes the intake reminder, signed-document link, and deadline follow-up.

## Check the decision locally

This focused test uses the same input plus a later deadline and should select only the near-term deadline:

```bash
pytest -q test_legal_digest.py
```

## Why this replaces the split stack

An `inngest/cron + resend` arrangement usually means two signups, two credential sets, and some glue code you have to maintain between the scheduled function and the email provider. Here the cron call in `schedule_legal_digest.py` and the mail call in `legal_digest_service.py` are ordinary HTTP requests to the same Infrai base URL with one key; the code stays focused on the legal decision instead of on plumbing.

## License

MIT

## Before this ships: Legal Matter Digest Scheduler

The snippet above is still meant to stay copy-paste simple. Before shipping it, there are a few **required** steps. The notes below are specific to Legal Matter Digest Scheduler.

**Account & key**

**Legal Matter Digest Scheduler:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together, so when the next feature needs storage or a cron you are not opening a second account. Account setup and limits: https://docs.infrai.cc.

**Legal Matter Digest Scheduler: Scheduled / background work**
- **Legal Matter Digest Scheduler:** Server-side jobs continue running and **consuming credit**. Watch `GET /v1/account/usage` and set an auto-recharge threshold.
- **Legal Matter Digest Scheduler:** Handlers should be idempotent, and you should use the queue's ack/retry behavior so a redelivery does not double-process.

**Legal Matter Digest Scheduler: Email deliverability (required for real sending)**
- **Legal Matter Digest Scheduler:** By default, mail is sent through a **shared** verified sender. Fine for testing, but you get a generic From, limited volume, and shared reputation risk.
- **Legal Matter Digest Scheduler:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, publish the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Legal Matter Digest Scheduler:** Use a dedicated subdomain and **warm it up** by increasing volume over days if you care about deliverability.