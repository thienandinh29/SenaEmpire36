# Demo upload consent

Uploads are disabled by default. Set `DEMO_UPLOADS_ENABLED=true` in the API and
worker environment only for the competition demo; apply migration `0011` first.
Keep `API_KEY` configured independently.

The upload dialog shows the exact Vietnamese notice from `SPEC.md`. The checkbox
starts unchecked and the file picker stays disabled until acceptance. The client
sends `X-Demo-Upload-Consent: demo-v1` only after acceptance; the same-origin proxy
forwards that exact value. Unchecking clears the selected upload from the form.

`POST /uploads` rejects disabled demo mode or missing/unknown consent before
reading the body, parsing a file, or fetching a link. Accepted uploads store
`uploads.demo_consent_at`. Old uploads have no consent timestamp. The worker
requires both demo mode and that persisted timestamp before indexing an upload or
sending its content to a model. `POST /topics` also rejects upload IDs outside demo
mode. There is no production permission implied by a previous demo consent.

Validation: API upload policy and persisted-consent/worker tests cover file and
link rejection, accepted uploads, missing consent, and disabled demo mode. Web
client/proxy tests cover refusal before consent and exact consent forwarding.
This does not establish provider privacy terms or authorize real-learner uploads.
