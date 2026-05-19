# Security Review Checklist

## Authentication & Session
- [ ] Passwords hashed with bcrypt or argon2 (not MD5, SHA1, or plain)
- [ ] JWT: algorithm explicitly set (never `alg: none`), secret in env var
- [ ] Session tokens: sufficient entropy, invalidated on logout
- [ ] Sensitive routes require auth check

## Authorization
- [ ] Every data access verifies ownership (IDOR check): `WHERE id = ? AND user_id = req.user.id`
- [ ] Admin routes have separate middleware, not just a role flag in the response
- [ ] No client-side-only authorization ("if (user.isAdmin) show button")

## Input Validation
- [ ] All user inputs validated (type, length, format) before processing
- [ ] Database queries use parameterized statements or ORM (no string concatenation)
- [ ] File uploads: type checked server-side, not just client-side

## Data Protection
- [ ] No secrets in code, config files, or logs (`grep -r "password\|secret\|api_key" src/`)
- [ ] Sensitive data in transit: HTTPS enforced (HSTS header)
- [ ] PII not logged in plain text

## API & Headers
- [ ] CORS: explicit allowed origins (no `*` in production)
- [ ] CSP header set (even if basic)
- [ ] Rate limiting on auth endpoints and expensive operations
- [ ] Error messages do not reveal internal details (no stack traces in 500 responses)

## Dependencies
- [ ] `npm audit` or equivalent: no critical or high vulnerabilities
- [ ] Dependencies are pinned or have lock file committed
- [ ] No abandoned packages (last release > 2 years, no maintainer)