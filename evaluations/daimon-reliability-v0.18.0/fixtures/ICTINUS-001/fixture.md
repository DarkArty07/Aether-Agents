# API proposal
POST /webhooks/payments uses provider_event_id as the idempotency key.
Persist event before asynchronous processing; duplicate events return 202.
