# Administration security — development milestone

- Administrator login uses a Werkzeug password hash supplied via UARMS_ADMIN_PASSWORD_HASH.
- UARMS_SECRET_KEY must be set to a long unpredictable value.
- Administration CRUD endpoints require a session. The login currently grants a single admin role.
- This is a **development-only** identity implementation, not production-ready multi-user RBAC.
- Before exposing to the internet: add CSRF protection, per-user accounts, rate limiting, HTTPS, session expiration, audit logs, account recovery, MFA and object-level permissions.
- Existing /api/academic read-only endpoints are NOT authenticated; do not populate them with real student records or deploy publicly until they are protected.
- Existing /api/excel/preview endpoint is also unauthenticated; protect it before real use.
- Never commit secret keys, password hashes, personal student data or real grades.
