---
name: data-source-evaluation
description: Evaluate external data APIs for viability — verify access, dimension TAM, sample data, measure fill rates, compare to alternatives. Use when researching any data source for B2B prospecting, enrichment, or market intelligence.
category: research
---

# Data Source Evaluation

Methodology for evaluating external data APIs (government, commercial, open) for viability in B2B prospecting or market intelligence workflows.

## Trigger
Use when: investigating an API or data source to determine if it provides sufficient coverage/quality for a prospecting or enrichment use case.

## Methodology (4 steps)

### 1. Verify Access
- Confirm API key/token works with a minimal call
- Use the cheapest endpoint (count, ping) to avoid wasting quota
- Check for rate limits (documented or empirical)

### 2. Dimension TAM
- Use count/aggregate endpoints to measure total coverage
- Query by industry, geography, and size filters relevant to the use case
- Record: total establishments, relevant segment size, geographic distribution

### 3. Sample Real Data
- Pull a small page (5-20 records) from the target segment
- Inspect ALL available fields
- Measure fill rates on contact-critical fields: email, phone, website, social
- Measure fill rates on classification fields: industry, size, location

### 4. Compare to Alternatives
- Build a comparison table: cost, coverage, contact fill rates, freshness
- Identify complementary strengths (one source for discovery, another for enrichment)
- Document what the source CANNOT provide

## Pitfalls
- Count endpoints may return per-entity breakdowns when passing wildcard area (0 or 00); sum manually or pass entity-specific codes
- Some APIs bill by SKU tier (highest field requested determines price) — know which fields trigger which tier
- Government APIs often have undocumented rate limits; implement backoff from day one
- Fill rates vary significantly by sector and company size — always segment samples
- **Tone when presenting findings**: Present fill rates and data as-is. Don't extrapolate to absolute claims ("this source is useless"). Let the numbers speak. If a source has 70% email coverage for IT but 10% phone coverage, say BOTH — not "the contact data is terrible" or "it's great."

## Support Files
- `references/denue-api-mexico.md` — INEGI DENUE API: endpoints, fill rates, SCIAN codes
- `references/hunter-io-mexico.md` — Hunter.io: coverage in Mexico by company tier, test results
- `references/google-places-api-pricing.md` — Google Places API (New): verified pricing, SKU mapping, 2-phase cost optimization
