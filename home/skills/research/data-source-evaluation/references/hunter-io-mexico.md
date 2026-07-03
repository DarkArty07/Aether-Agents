# Hunter.io — Coverage in Mexico

## Summary
Hunter.io finds emails published on the public internet. Coverage in Mexico is HIGHLY variable: excellent for multinationals with Mexican presence, poor for PyMEs and some large Mexican companies.

## API Quick Reference
- **Endpoint**: `GET https://api.hunter.io/v2/domain-search?domain=DOMAIN&api_key=KEY`
- **Auth**: API key as query param
- **Pricing**: Credit-based (1 credit per domain search, paid plans start ~$49/mo for 500 searches)
- **Key params**: `domain`, `limit`, `seniority`, `department`, `type`

## Test Results — Mexican Domains (4 domains tested)

| Domain | Emails Found | Quality |
|--------|-------------|---------|
| hsbc.com.mx | **201** | Excellent. Names, positions, departments. Confidence 94%. Pattern: `{first}.{last}` |
| cinemex.com.mx | **2** | Moderate. `buzon@` (generic, 94%) + `cameronpoe@` (personal, 80%) |
| televisa.com | **0** | Domain recognized, pattern `{f}{last}`, but zero public emails indexed |
| solsoft.com.mx | **0** | Domain not recognized, no pattern detected |

## Pattern
Hunter.io indexes emails found in public documents (PDFs, web pages, directories). Mexican companies publish fewer emails publicly than US companies, so coverage drops sharply below the multinational tier.

- **Multinationals with MX presence** → Excellent (201 emails for HSBC)
- **Large Mexican companies** → Variable (2 for Cinemex, 0 for Televisa)
- **PyMEs** → Near zero (0 for Solsoft)

## Key Fields in Response
```json
{
  "data": {
    "domain": "cinemex.com.mx",
    "pattern": "{last}",
    "organization": "Cinemex",
    "accept_all": false,
    "emails": [{
      "value": "buzon@cinemex.com.mx",
      "type": "personal",
      "confidence": 94,
      "first_name": null,
      "last_name": null,
      "position": null,
      "department": null,
      "sources": [{"domain": "...", "uri": "...", "extracted_on": "...", "last_seen_on": "..."}]
    }]
  },
  "meta": {"results": 2}
}
```

## Important: `accept_all` Flag
- `true` = email server accepts all addresses (can't verify validity via SMTP)
- HSBC Mexico has `accept_all: true` — emails likely valid but verification impossible
- Pattern knowledge alone is still useful for email guessing

## Integration Strategy for Mexico
Hunter.io alone is INSUFFICIENT for Mexican B2B prospecting. Best used as:
1. **Waterfall after DENUE**: DENUE provides domain → Hunter.io does domain search → returns emails if published
2. **Email verification**: Use Hunter.io verifier endpoint on emails found via other sources
3. **Pattern discovery**: Even with 0 results, Hunter.io often returns the email pattern (e.g., `{f}{last}`, `{first}.{last}`) which enables email guessing for other contacts
