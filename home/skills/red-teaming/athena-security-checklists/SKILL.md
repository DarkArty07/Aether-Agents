---
name: athena-security-checklists
description: Detailed security review checklists, dependency audit protocol, and few-shot examples for Athena. Loaded on-demand during security reviews.
version: 1.0.0
category: red-teaming
triggers:
  - When performing a detailed security review
  - When running a STRIDE threat model with full checklists
  - When Athena needs few-shot examples for output format
  - When performing a dependency audit
---

# Athena Security Checklists

Detailed protocols and examples for security assessments. Athena's SOUL.md contains compact versions; this skill provides the full detail.

## Security Review Checklist

### Authentication & Session
- [ ] Passwords hashed with bcrypt or argon2 (not MD5, SHA1, or plain)
- [ ] JWT: algorithm explicitly set (never `alg: none`), secret in env var
- [ ] Session tokens: sufficient entropy, invalidated on logout
- [ ] Sensitive routes require auth check

### Authorization
- [ ] Every data access verifies ownership (IDOR check): `WHERE id = ? AND user_id = req.user.id`
- [ ] Admin routes have separate middleware, not just a role flag in the response
- [ ] No client-side-only authorization ("if (user.isAdmin) show button")

### Input Validation
- [ ] All user inputs validated (type, length, format) before processing
- [ ] Database queries use parameterized statements or ORM (no string concatenation)
- [ ] File uploads: type checked server-side, not just client-side

### Data Protection
- [ ] No secrets in code, config files, or logs (`grep -r "password\|secret\|api_key" src/`)
- [ ] Sensitive data in transit: HTTPS enforced (HSTS header)
- [ ] PII not logged in plain text

### API & Headers
- [ ] CORS: explicit allowed origins (no `*` in production)
- [ ] CSP header set (even if basic)
- [ ] Rate limiting on auth endpoints and expensive operations
- [ ] Error messages do not reveal internal details (no stack traces in 500 responses)

### Dependencies
- [ ] `npm audit` or equivalent: no critical or high vulnerabilities
- [ ] Dependencies are pinned or have lock file committed
- [ ] No abandoned packages (last release > 2 years, no maintainer)

## Dependency Audit Protocol

When Hermes requests a dependency audit:

1. **Identify critical dependencies**: From `package.json`, `pyproject.toml`, or `requirements.txt`
2. **For each critical dependency** (auth, crypto, DB adapter, web framework):
   - Note current version
   - Check for known CVEs: `npm audit`, `pip audit`, or request Etalides to research
   - Check maintenance: releases in last 12 months, active maintainer, open issues ratio
3. **Prioritize**: Critical > High > Medium > Low
4. **If CVE research needed**: Ask Hermes to route to Etalides. Do NOT do web research yourself.

## Few-Shot Examples

### Example A — Auth Flow Threat Model (Magic Link)

Hermes sends:
```
CONTEXT: Implementing magic link authentication. User enters email → server generates JWT (15min expiry) → email sent → user clicks → JWT validated → session created.
TASK: Threat model this flow. Identify threats and required mitigations.
OUTPUT: Standard Athena format.
```

Athena returns:
```
## Security Assessment: Magic Link Authentication Flow

### Threats Identified

1. **Token Theft via Email Interception**
   - Type: S (Spoofing)
   - Severity: High | Likelihood: Low
   - Attack vector: Attacker intercepts email in transit or gains access to email account
   - Impact: Attacker logs in as victim
   - Mitigation: Short expiry (15min ✓), token single-use (invalidate after first use), bind token to user agent or IP optionally

2. **Token Reuse**
   - Type: S (Spoofing) / E (Elevation)
   - Severity: High | Likelihood: Medium
   - Attack vector: User clicks link → logs in. Attacker finds link in browser history or email and uses it again.
   - Impact: Second valid session created for attacker
   - Mitigation: **Invalidate token immediately after first use** (not just on expiry)

3. **Email Enumeration**
   - Type: I (Information Disclosure)
   - Severity: Low | Likelihood: High
   - Attack vector: Attacker submits emails to magic link endpoint. Different response for "email found" vs "email not found" reveals registered users.
   - Impact: Attacker builds list of valid user emails
   - Mitigation: Always respond "If email exists, we sent a link" — same response regardless

4. **Magic Link Endpoint Abuse (DoS)**
   - Type: D (Denial of Service)
   - Severity: Medium | Likelihood: Medium
   - Attack vector: Automated requests flood the endpoint, triggering mass email sends
   - Impact: Email provider rate limits hit, legitimate users cannot receive links
   - Mitigation: Rate limit the magic link request endpoint (e.g., 5 requests/email/hour)

### Recommendations (Prioritized)
1. **CRITICAL**: Invalidate token after single use in the database (not just check expiry)
2. **HIGH**: Rate limit magic link endpoint per email address
3. **MEDIUM**: Same response message whether email exists or not
4. **LOW**: Consider binding token to User-Agent for extra defense-in-depth

### Residual Risk
- Email account compromise still allows attacker to log in as user. Acceptable unless MFA is added (separate decision).
- Token theft via HTTPS interception: negligible if HTTPS enforced (verify HSTS header).

### Confidence: high
Based on: full flow spec provided. Code review not performed — recommendations based on spec analysis.
```

### Example B — Pre-Deploy Security Check (Payment Module)

Hermes sends:
```
CONTEXT: Payment module ready for deploy. Includes Stripe.js frontend + webhook handler.
TASK: Quick security check before deploy. Focus on webhook and data handling.
OUTPUT: Standard Athena format.
```

Athena returns:
```
## Security Assessment: Payment Module — Pre-Deploy

### Threats Identified

1. **Webhook Signature Not Verified**
   - Type: T (Tampering)
   - Severity: Critical | Likelihood: High
   - Attack vector: Attacker sends fake Stripe webhook payloads to /webhooks/stripe, marking orders as paid without real payment
   - Impact: Revenue loss, fraudulent orders marked complete
   - Mitigation: Verify `stripe-signature` header using `stripe.webhooks.constructEvent()` on raw body (not parsed JSON)

2. **Webhook Body Parsed Before Signature Check**
   - Type: T (Tampering)
   - Severity: High | Likelihood: High (common implementation mistake)
   - Attack vector: If body is parsed by Express JSON middleware before reaching webhook handler, signature verification will fail for all real Stripe events
   - Impact: Either all Stripe webhooks fail, or signature check is disabled to "fix" it
   - Mitigation: Use `express.raw()` middleware specifically for the Stripe webhook route, NOT `express.json()`

### Recommendations (Prioritized)
1. **CRITICAL**: Confirm webhook handler uses `express.raw()` — show the route configuration
2. **CRITICAL**: Confirm `stripe.webhooks.constructEvent()` is called before any business logic
3. **MEDIUM**: Log webhook events with idempotency key for debugging (without logging full card data)

### Residual Risk
- Stripe.js handles card data entirely client-side — PCI scope is reduced. No card data touches your backend. This is the correct architecture.

### Confidence: medium
Based on: architectural description. Full code review not performed. Recommend code review of webhook handler specifically by Hefesto (role: security) before deploy.
```