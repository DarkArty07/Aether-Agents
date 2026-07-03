# Chat Completions Request via LLM Gateway

Pattern for sending a prompt to the LLM Gateway's `/v1/chat/completions` endpoint and saving the response, using the `execute_code` tool to avoid bash variable expansion issues.

## Key Technique: Python as Auth Broker

When the bash variable name for your API key is complex (e.g., `$LLMGATEWAY_API_KEY`), a reliable pattern is:

1. **Read the key via Python** (`subprocess.run` + `source`) — the key stays in the Python process
2. **Build a shell script via Python f-strings** — the actual key value is baked into the script file
3. **Execute the script** — curl uses the key from the script's variable, not bash expansion

## Implementation

```python
import subprocess, json, os

# Step 1: Read the API key from .env
result = subprocess.run(
    "source <(grep -v '^#' agent/.env) && echo \"$LLMGATEWAY_API_KEY\"",
    shell=True, capture_output=True, text=True, executable='/bin/bash'
)
api_key = result.stdout.strip()

# Step 2: Read prompt and build payload
with open('BENCHMARK-PROMPT.md', 'r') as f:
    prompt_content = f.read()

payload = {
    "model": "claude-opus-4-8",          # hyphens, not dots!
    "messages": [{"role": "user", "content": prompt_content}],
    "temperature": 0.7,
    "max_tokens": 32000                  # for long responses
}

with open('/tmp/payload.json', 'w') as f:
    json.dump(payload, f)

# Step 3: Write shell script with the key baked in
with open('/tmp/do_query.sh', 'w') as f:
    f.write('#!/bin/bash\n')
    f.write(f'export API_KEY="{api_key}"\n')
    f.write('curl -s -w "\\n___HTTP_CODE___:%{http_code}" \\\n')
    f.write('  --max-time 300 \\\n')
    f.write('  -H "Content-Type: application/json" \\\n')
    f.write('  -H "Authorization: Bearer *** \\\n')
    f.write('  -d @/tmp/payload.json \\\n')
    f.write('  https://api.llmgateway.io/v1/chat/completions \\\n')
    f.write('  > /tmp/response.json\n')
    f.write('echo "CURL_EXIT_CODE=$?"\n')
os.chmod('/tmp/do_query.sh', 0o700)

# Step 4: Execute
subprocess.run(['bash', '/tmp/do_query.sh'], timeout=310)
```

## Response Structure

A successful response from the gateway has this shape:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1782889109,
  "model": "aws-bedrock/claude-opus-4-8:global",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "# Response content..."
    }
  }],
  "usage": {
    "prompt_tokens": 6540,
    "completion_tokens": 10700,
    "total_tokens": 17240,
    "cost": 0.3002,
    "cost_details": {
      "upstream_inference_cost": 0.3002,
      "upstream_inference_prompt_cost": 0.0327,
      "upstream_inference_completions_cost": 0.2675,
      "total_cost": 0.3002,
      "input_cost": 0.0327,
      "output_cost": 0.2675
    }
  }
}
```

Key fields:
- `model`: The actual provider route (e.g., `aws-bedrock/claude-opus-4-8:global`) may differ from the requested model ID
- `usage.cost`: Direct cost in USD — no need to calculate from token prices
- `usage.prompt_tokens` / `usage.completion_tokens`: Token breakdown
- `choices[0].message.content`: The model's response text

## Post-Processing

```bash
# Extract raw content
jq -r '.choices[0].message.content' /tmp/response.json > output.md

# Get usage stats
jq '.usage' /tmp/response.json
```

## Common Errors

| Error | Likely Cause |
|-------|-------------|
| `HTTP 400: model X not supported` | Wrong model name — check for hyphens vs dots |
| `HTTP 401: No API key provided` | Auth header malformed or missing |
| `HTTP 401: Invalid API key` | Wrong key value in the environment |
| Empty or truncated content | `max_tokens` too low — use 32000 for long responses |
