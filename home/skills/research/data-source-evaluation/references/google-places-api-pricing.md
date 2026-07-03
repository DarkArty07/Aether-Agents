# Google Places API (New) — Verified Pricing

Source: mapsplatform.google.com/pricing/ — extracted from the `pricingData` JSON.

## Nearby Search SKUs (for B2B prospecting)

| SKU | USD/1,000 | Free/mo | Includes | SKU ID |
|-----|-----------|---------|----------|--------|
| **Nearby Search Pro** | $32 | 5,000 | Name, Address, Location, Business Status, Types | 99F9-A108-83A6 |
| **Nearby Search Enterprise** | $35 | 1,000 | + Phone, Website (Contact Data) | 772E-9975-BE34 |
| **Nearby Search Enterprise + Atmosphere** | $40 | 1,000 | + Rating, Reviews, Atmosphere Data | F20E-7034-0EF7 |

## Critical Billing Rule
Google bills at the HIGHEST SKU touched in a request. If you request Rating (Atmosphere field), the ENTIRE call is billed at Enterprise + Atmosphere ($40/1,000).

## Tier Structure (all Nearby Search SKUs follow this)

| Tier | Volume Range | Unit Cost |
|------|-------------|-----------|
| 1 | 0–100K/mo | $32-40 (base) |
| 2 | 100K–500K | 80% of base |
| 3 | 500K–1M | 60% of base |
| 4 | 1M–5M | 30% of base |
| 5 | 5M–10M | 7.5% of base |

## Field Mapping for Prospecting

### Phase 1 — Discovery (Pro, $32/1,000)
`places.displayName`, `places.formattedAddress`, `places.location`, `places.businessStatus`, `places.types`

### Phase 2 — Enrichment (Enterprise, $35/1,000)
`places.nationalPhoneNumber`, `places.websiteUri`

### Phase 2+ — Full (Enterprise + Atmosphere, $40/1,000)
`places.rating`, `places.userRatingCount`, `places.reviews`

## Cost per Lead by Volume (Enterprise + Atmosphere)

| Volume/mo | Google API (USD) | ~MXN ($19/USD) | Cost per lead (MXN) |
|-----------|-----------------|----------------|---------------------|
| 1,000 | $0 (free) | $0 | $0 |
| 5,000 | $160 | ~$3,040 | $0.61 |
| 10,000 | $360 | ~$6,840 | $0.68 |
| 100,000 | $3,990 | ~$75,800 | $0.75 |

## Two-Phase Architecture (Cost Optimization)

- **Phase 1**: Nearby Search PRO ($32/1,000, 5K free/mo) — Name + Address only
- Filter out ~70% irrelevant (B2C, wrong zone, wrong industry)
- **Phase 2**: Enterprise + Atmosphere ($40/1,000, 1K free/mo) — only for filtered 30%

| Volume | No filter | 2-phase | Savings |
|--------|----------|---------|---------|
| 10,000 | $360 | ~$148 | 59% |
| 100,000 | $3,990 | ~$1,576 | 60% |

## Clay Markup Comparison

Clay charges ~$185/mo for 2,500 credits (~$0.074/credit ≈ $1.40 MXN/lead). Google API direct saves 25-57% vs Clay, plus 60% more with 2-phase architecture.
