# Hindsight Embedding & Reranker Model Benchmarks

Research from May 2026 session. Covers local and API embedding/reranker models relevant to Hindsight's memory provider for agent memory use cases.

## Key Insight

For **agent memory** (Hindsight), the real bottleneck is the `reflect` LLM call (1-3s per turn to DeepSeek V4 Flash), NOT the embedding or reranking step (<20ms combined). The default local models are optimal for this use case.

## Default Models (Shipped with Hindsight local_embedded)

### BAAI/bge-small-en-v1.5 (Embeddings)

| Metric | Value |
|--------|-------|
| Parameters | 33M (0.033B) |
| Dimensions | 384 |
| Max context | 512 tokens |
| VRAM | ~0.1 GB (BF16) |
| Disk size | ~130 MB |
| CPU latency | ~2-5 ms per text |
| CPU throughput | ~500-1000 texts/sec |
| MTEB Score (56 tasks) | 62.17 |
| MTEB Retrieval | 51.68 |

### cross-encoder/ms-marco-MiniLM-L-6-v2 (Reranker)

| Metric | Value |
|--------|-------|
| Parameters | 22.7M |
| CPU latency | ~30ms per batch of 16 pairs |
| CPU latency | ~5-10ms for 10-20 candidates |
| Disk size | ~80 MB |
| MRR@10 (MS MARCO) | 39.01% |
| NDCG@10 (TREC DL 19) | 74.30% |
| Throughput (V100 GPU) | ~1800 docs/sec |

Both run on CPU, no GPU needed. Auto-downloaded on first daemon start.

---

## Local Embedding Model Alternatives

All free, self-hosted. Latency measured on CPU unless noted.

| Model | Params | Dims | MTEB | Retrieval | CPU Latency | Disk | Notes |
|-------|--------|------|------|-----------|-------------|------|-------|
| **bge-small-en-v1.5** (current) | 33M | 384 | 62.2 | 51.7 | ~5ms | 130MB | Default. Best speed. |
| bge-base-en-v1.5 | 110M | 768 | 63.6 | 53.3 | ~15ms | 430MB | Best free upgrade (+1.4 MTEB) |
| bge-large-en-v1.5 | 335M | 1024 | 64.2 | 54.3 | ~45ms | 1.3GB | Diminishing returns |
| Qwen3-Embedding-0.6B | 600M | Variable | 64.3 | 56.0 | ~8ms GPU | 1.2GB | Needs GPU or TEI. Best local quality/size. |
| Qwen3-Embedding-8B | 8B | 4096 | 70.6 | 70.9 | ~30ms GPU | 16GB VRAM | SOTA open-source. Overkill for agent memory. |
| BGE-M3 | 568M | 1024 | 62.8 | — | ~50ms | ~560MB | Multilingual (100+ langs). Hybrid dense+sparse. |
| multilingual-e5-large | 560M | 1024 | 63.2 | — | — | ~560MB | Strong multilingual. |

**Recommendation for Hindsight:** Stay on bge-small-en-v1.5. If recall quality feels insufficient, upgrade to bge-base-en-v1.5 (same provider, just change `HINDSIGHT_API_EMBEDDINGS_LOCAL_MODEL`). The +1.4 MTEB gain is marginal for agent memory but costs nothing extra.

## API Embedding Model Alternatives

All require network, add latency (80-300ms round trip), and incur cost.

| Model | Provider | Dims | MTEB | Retrieval | Cost/1M tok | Latency | Notes |
|-------|----------|------|------|-----------|-------------|---------|-------|
| text-embedding-3-small | OpenAI | 1536 | 62.3 | — | $0.02 | ~80ms | Cheap API option |
| text-embedding-3-large | OpenAI | 3072 | 64.6 | ~68 | $0.13 | ~120ms | Best OpenAI quality |
| gemini-embedding-001 | Google | 768 | 68.4 | 66.0 | ~$0.025 | ~100ms | Best API MTEB score |
| embed-english-v3.0 | Cohere | 1024 | — | — | $0.10 | ~90ms | Strong classification |
| Voyage-3 | Voyage | 1024 | 64.8 | — | $0.06 | ~80ms | Great RAG quality |
| Jina v3 | Jina | 1024 | 65.2 (v3) | — | $0.02 | ~50ms | Good + multilingual |

**Why NOT use API embeddings for Hindsight:**
1. Network latency (80-300ms) >> local latency (5ms) on every search
2. Persistent cost per query ($2-5/mo estimated with text-embedding-3-large)
3. Dependency on third-party uptime — memory breaks if API is down
4. MTEB gain of 2-6 points doesn't translate proportionally to better agent memory recall (short conversational queries, not long documents)

## Reranker Alternatives

### Local (Free)

| Model | NDCG@10 | MRR@10 | CPU Latency | Disk | Notes |
|-------|---------|--------|-------------|------|-------|
| **ms-marco-MiniLM-L-6-v2** (current) | 74.30 | 39.01 | ~30ms/batch | 80MB | Best CPU reranker. |
| ms-marco-TinyBERT-L-2-v2 | 69.84 | 32.56 | ~15ms | ~30MB | Fastest. Lower quality. |
| ms-marco-MiniLM-L-4-v2 | 73.04 | 37.70 | ~50ms | ~250MB | Marginally slower than L-6. |
| ms-marco-MiniLM-L-12-v2 | 74.31 | 39.02 | ~100ms | ~420MB | Same quality as L-6, 3x slower. |
| bge-reranker-v2-m3 | 69.32 (BEIR) | — | ~100ms | ~568MB | Multilingual. Worse English reranking. |
| jina-reranker-v3 | 61.94 (BEIR) | — | ~50ms | ~600MB | New listwise approach. Jury still out. |

### API (Paid)

| Model | Cost/1K queries | Quality | Latency | Notes |
|-------|-----------------|---------|---------|-------|
| Cohere rerank-english-v2 | $1 | +25% over baseline | +200ms | Easiest setup |
| Cohere rerank-multilingual-v2 | $1 | Good multilingual | +200ms | Best for non-English |

**Recommendation for Hindsight:** Stay on ms-marco-MiniLM-L-6-v2. It's the sweet spot for CPU reranking. L-12 matches quality but is 3x slower. bge-reranker-v2-m3 is worse at English reranking. Paid rerankers add network latency for negligible quality gain.

## Hindsight Configuration: Changing Models

### Embeddings (config.json or env vars)

```bash
# Local model change (free, just different model)
export HINDSIGHT_API_EMBEDDINGS_PROVIDER=local
export HINDSIGHT_API_EMBEDDINGS_LOCAL_MODEL=BAAI/bge-base-en-v1.5

# Or in ~/.hindsight/profiles/hermes.env:
# HINDSIGHT_API_EMBEDDINGS_PROVIDER=local
# HINDSIGHT_API_EMBEDDINGS_LOCAL_MODEL=BAAI/bge-base-en-v1.5

# Switch to OpenAI (costs money, adds latency)
# HINDSIGHT_API_EMBEDDINGS_PROVIDER=openai
# HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY=sk-xxx
# HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL=text-embedding-3-small

# Switch to Google (costs money, adds latency)
# HINDSIGHT_API_EMBEDDINGS_PROVIDER=google
# HINDSIGHT_API_EMBEDDINGS_GEMINI_API_KEY=xxx
# HINDSIGHT_API_EMBEDDINGS_GEMINI_MODEL=gemini-embedding-001
```

**CRITICAL:** Changing embedding model dimensions (e.g., 384 → 768) requires resetting the database. Existing memories stored with 384-dim vectors will NOT be compatible with a 768-dim model. Options:
1. Empty database — schema adjusts automatically on startup
2. Existing data — either delete all memories first, or use a model with matching dimensions

### Reranker (env vars only)

Hindsight uses `cross-encoder/ms-marco-MiniLM-L-6-v2` by default. There is no documented env var for changing the reranker model in local_embedded mode — it auto-downloads and uses this model. To use a different reranker, switch to TEI mode or an API provider.

### Supported Hindsight Embedding Providers

| Provider | Env prefix | Supported models |
|----------|------------|-----------------|
| `local` | `HINDSIGHT_API_EMBEDDINGS_LOCAL_` | Any SentenceTransformers model |
| `openai` | `HINDSIGHT_API_EMBEDDINGS_OPENAI_` | text-embedding-3-small, text-embedding-3-large, ada-002 |
| `cohere` | `HINDSIGHT_API_EMBEDDINGS_COHERE_` | embed-english-v3.0, embed-multilingual-v3.0 |
| `google` | `HINDSIGHT_API_EMBEDDINGS_GEMINI_` | gemini-embedding-001 |
| `tei` | `HINDSIGHT_API_EMBEDDINGS_TEI_URL` | Any TEI-served model |
| `litellm` | `HINDSIGHT_API_LITELLM_` | Any LiteLLM-supported embedding model |
| `litellm-sdk` | `HINDSIGHT_API_EMBEDDINGS_LITELLM_SDK_` | Direct LiteLLM SDK access |

### Minimum Viable Upgrade Path

If recall quality is insufficient and you want to improve:

1. **Free, same performance characteristics**: Change to `BAAI/bge-base-en-v1.5` (+1.4 MTEB, same CPU, 430MB disk). Requires DB reset.

2. **Free, GPU-accelerated**: Change to `Qwen3-Embedding-0.6B` via TEI (+2.1 MTEB, needs GPU or slow CPU). Requires DB reset + TEI docker.

3. **Paid, simplest API**: Switch to `google` + `gemini-embedding-001` (+6.2 MTEB). Adds ~100ms network latency, ~$0.025/1M tokens. Requires DB reset.

4. **Paid, best API quality**: Switch to `openai` + `text-embedding-3-large` (+2.4 MTEB over current). Adds ~120ms latency, $0.13/1M tokens. Requires DB reset.

## Benchmark Sources

- MTEB Leaderboard (mteb leaderboard / codesota.com/benchmarks/mteb)
- BGE v1/v1.5 model cards (HuggingFace)
- cross-encoder/ms-marco-MiniLM-L-6-v2 model card (HuggingFace)
- PrecisionAI Academy embedding model benchmark (precisionaiacademy.com)
- Jina reranker v3 announcement (jina.ai)
- clouatre-labs/rag-reranking-benchmarks (GitHub)
- AgentSet reranker comparison (agentset.ai)
- TrackAI embedding selection guide (trackai.dev)