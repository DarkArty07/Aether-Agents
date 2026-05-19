# Few-Shot Examples

## Example A — Auth Flow Threat Model (Magic Link)

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

## Example B — Pre-Deploy Security Check (Payment Module)

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