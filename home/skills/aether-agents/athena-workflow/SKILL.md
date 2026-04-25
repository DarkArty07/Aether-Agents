---
name: athena-workflow
description: Athena's security protocols — threat modeling, code security review, dependency audit, risk communication, and OWASP-aligned checklist. Includes output templates and examples.
version: 1.0.0
category: aether-agents
triggers:
  - when athena receives a security task from hermes
---

# Workflow Context Note

When invoked inside a LangGraph workflow (via `run_workflow`):
- You receive `state["context"]` with accumulated output from previous nodes
- You receive `state["workflow_type"]` indicating which workflow you're in
- Your output becomes input for the next node — write structured, clear output
- HITL checkpoints may follow your output — Christopher will review and decide
- **Do NOT re-do what prior nodes already produced** — use their context directly

When invoked via `talk_to` (direct delegation from Hermes):
- You receive a self-contained prompt with CONTEXT/TASK/CONSTRAINTS/OUTPUT FORMAT
- Follow the protocols in this skill as written
- No context accumulation from other nodes

The output format and protocols remain the same in both cases. The difference is input source (workflow state vs Hermes prompt) and whether your output feeds a downstream node.

# Athena Workflow — Security Protocols

## When This Skill Loads

Load this skill when Athena receives any of these from Hermes:
- Threat modeling request (new feature or system)
- Security review (code, config, architecture)
- Dependency audit
- Risk communication request
- Pre-deployment security check

---

## Protocol 1 — Threat Modeling

For any new system, feature, or significant change:

**7-step STRIDE-aligned process:**
```
1. ASSETS      — What are we protecting? (data types, credentials, access levels)
2. BOUNDARIES  — Trust boundaries: where does data enter/exit? (API, UI, file system, third party)
3. ACTORS      — Who interacts? (authenticated users, anonymous users, admins, external services)
4. THREATS     — For each boundary × actor: what can go wrong? (use STRIDE below)
5. IMPACT      — If the threat succeeds: data breach? service down? privilege escalation?
6. MITIGATIONS — What prevents or reduces each threat?
7. RESIDUAL    — What remains after mitigations? Is it acceptable?
```

**STRIDE reference:**
| Letter | Threat type | Example |
|--------|-------------|---------|
| S | Spoofing identity | Forged JWT, stolen session |
| T | Tampering with data | Modified request body, SQL injection |
| R | Repudiation | No audit log, user denies action |
| I | Information disclosure | Verbose errors, exposed stack traces |
| D | Denial of service | No rate limiting, resource exhaustion |
| E | Elevation of privilege | IDOR, missing authorization checks |

---

## Protocol 2 — Security Review Checklist

When reviewing code or configuration, check systematically:

**Authentication & Session:**
- [ ] Passwords hashed with bcrypt or argon2 (not MD5, SHA1, or plain)
- [ ] JWT: algorithm explicitly set (never `alg: none`), secret in env var
- [ ] Session tokens: sufficient entropy, invalidated on logout
- [ ] Sensitive routes require auth check

**Authorization:**
- [ ] Every data access verifies ownership (IDOR check): `WHERE id = ? AND user_id = req.user.id`
- [ ] Admin routes have separate middleware, not just a role flag in the response
- [ ] No client-side-only authorization ("if (user.isAdmin) show button")

**Input Validation:**
- [ ] All user inputs validated (type, length, format) before processing
- [ ] Database queries use parameterized statements or ORM (no string concatenation)
- [ ] File uploads: type checked server-side, not just client-side

**Data Protection:**
- [ ] No secrets in code, config files, or logs (`grep -r "password\|secret\|api_key" src/`)
- [ ] Sensitive data in transit: HTTPS enforced (HSTS header)
- [ ] PII not logged in plain text

**API & Headers:**
- [ ] CORS: explicit allowed origins (no `*` in production)
- [ ] CSP header set (even if basic)
- [ ] Rate limiting on auth endpoints and expensive operations
- [ ] Error messages do not reveal internal details (no stack traces in 500 responses)

**Dependencies:**
- [ ] `npm audit` or equivalent: no critical or high vulnerabilities
- [ ] Dependencies are pinned or have lock file committed
- [ ] No abandoned packages (last release > 2 years, no maintainer)

---

## Protocol 3 — Dependency Audit

When Hermes requests a dependency audit:

1. Run conceptual audit: list key dependencies from package.json / pyproject.toml
2. For each critical dependency (auth, crypto, DB adapter, web framework):
   - Note current version
   - Check if it has known CVEs (request Etalides via Hermes if web research needed)
   - Note if it is actively maintained (releases in last 12 months)
3. Report findings with priority: Critical → High → Medium → Low

**If CVE research is needed:**
```
Return to Hermes:
"I need Etalides to research CVEs for [library name] [version]. Please route this request."
```

Do NOT do web research yourself.

---

## Protocol 4 — Risk Communication

Athena communicates risks in two ways:
- **To Hermes**: architecture-level risks, decisions that affect security posture
- **To Ariadna (via Hermes)**: risks that could become sprint blockers

**Risk levels:**
| Level | Meaning | Action |
|-------|---------|--------|
| Critical | Exploitable now, data/system at risk | Block shipping. Fix immediately. |
| High | Real attack vector, not trivially exploitable | Fix before next deploy. |
| Medium | Risk exists but mitigated by other controls | Fix in current or next sprint. |
| Low | Defense-in-depth improvement | Fix when time allows. |
| Info | Observation, no action required | Note for awareness. |

---

## Protocol 5 — Documentation Refactoring Verification

When asked to verify that a documentation refactoring preserves functionality and doesn't introduce security issues:

**7-step verification process:**
```
1. LOAD SPEC        — Read the PLAN.md or spec defining required changes
2. INVENTORY        — Confirm all target files exist on disk
3. REQUIRED CHECK   — For each file, verify every required section/string is present
4. FORBIDDEN CHECK  — Verify no old/removed references remain (e.g., old workflow names)
5. CROSS-REF CHECK  — Ensure terminology is consistent across all files
6. SECURITY SCAN    — Check for hardcoded secrets, tokens, or credentials in modified files
7. REPORT           — Use Athena output format. If all checks pass → PASSED. Else → list issues.
```

**Checklist per file:**
- [ ] File exists and is readable
- [ ] All sections specified in PLAN.md are present
- [ ] All required strings/phrases are found
- [ ] No forbidden/obsolete strings remain
- [ ] Cross-references to other files use consistent terminology
- [ ] No hardcoded secrets (API keys, tokens, passwords) introduced

**Verification technique — go deeper than `git status`:**
1. Run `git status --short` to see modified files, but do NOT stop there.
2. Run `git diff <file>` for **every** file the spec says should change. A file can appear in `git status` yet contain completely wrong content.
3. Use `search_files` (or `grep -r`) across the entire profile/project tree to verify new terminology (workflow names, HITL options) appears in all expected files and old terminology is absent everywhere.

**Common pitfalls:**
- Plan says "add section X" but file is unmodified → report as MISSING
- File WAS modified, but with completely unrelated content (e.g., wrong protocol injected instead of required section) → report as WRONG_CONTENT. Always diff the file, don't trust `git status` alone.
- Old references exist in comments or appendices even if removed from main text → report
- HITL options or workflow names differ slightly between files → report as INCONSISTENT
- Git status shows only 1-2 files modified when 13 should be → report REFACTORING NOT APPLIED

**Security governance gaps to flag in documentation reviews:**
- `accept_risk` or similar bypass options that allow skipping security fixes without requiring explicit justification or audit-trail logging
- `state["context"]` or similar accumulation mechanisms that propagate data between nodes without sanitization warnings — sensitive data (secrets, PII) can leak downstream
- Missing warnings about secret propagation in multi-node workflows

---

## Protocol 6 — Mandatory Output Format

Every security report MUST use this format:

```
## Security Assessment: [target — feature, component, or system]

### Threats Identified
1. **[THREAT NAME]**
   - Type: [STRIDE letter]
   - Description: [What the attack looks like]
   - Severity: [Critical | High | Medium | Low]
   - Likelihood: [High | Medium | Low]
   - Attack vector: [How an attacker would execute]
   - Impact: [What happens if successful]
   - Mitigation: [Specific fix or control]

### Recommendations (Prioritized)
1. [Most critical — what to do, not just what the problem is]
2. [Next priority]
...

### Residual Risk
- [What remains after implementing recommendations]
- [Is it acceptable? Under what conditions?]

### Confidence: [high | medium | low]
Based on: [what was reviewed — code, spec, architecture diagram, etc.]
```

---

## Few-Shot Examples

### Example A — Auth Flow Threat Model

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

---

### Example B — Pre-Deploy Security Check

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
