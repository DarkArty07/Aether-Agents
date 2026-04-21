# Hermes Profile Setup

How to configure your environment so that the `hermes` command always starts the
Hermes Daimon (orchestrator) from Aether Agents — not the default personal profile.

---

## How it works

Aether Agents uses a custom `HERMES_HOME` that points to the project directory
instead of the default `~/.hermes/`. Inside that directory, each Daimon has its
own profile under `home/profiles/<name>/`.

```
~/Aether-Agents/
└── home/                        ← HERMES_HOME
    ├── config.yaml              ← global fallback config (auto-generated)
    ├── active_profile           ← tells hermes which profile to use by default
    └── profiles/
        └── hermes/              ← Hermes Daimon profile
            ├── config.yaml      ← profile config (auto-generated from template)
            ├── config.yaml.template
            └── .env             ← API keys (never committed)
```

When `hermes` starts, it reads `HERMES_HOME` from the environment, then checks
`active_profile` to determine which profile to load. No `-p` flag needed.

---

## Step 1 — Set HERMES_HOME

Add this to your `~/.bashrc` (or `~/.zshrc`):

```bash
export HERMES_HOME=/path/to/Aether-Agents/home
```

Replace `/path/to/Aether-Agents` with the actual path where you cloned the repo.

Reload your shell:

```bash
source ~/.bashrc
```

---

## Step 2 — Generate the profile config

Run the configure script once after cloning. It substitutes the machine-specific
paths in the templates:

```bash
bash scripts/configure.sh
```

This generates:
- `home/config.yaml` from the global template
- `home/profiles/hermes/config.yaml` from `config.yaml.template`

---

## Step 3 — Set the active profile

Create the `active_profile` file so `hermes` loads the Hermes Daimon by default:

```bash
echo "hermes" > home/active_profile
```

After this, running `hermes` is equivalent to `hermes -p hermes`. No flags needed.

---

## Step 4 — Configure the API key (z.ai Coding Plan)

The Hermes Daimon uses GLM-5.1 via [z.ai](https://z.ai) on the Coding Plan.

1. Log in to [z.ai](https://z.ai)
2. Go to **API Keys** and generate a new key
3. Copy the key (format: `xxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxxxxxxxxxx`)
4. Open `home/profiles/hermes/.env` and set:

```bash
GLM_API_KEY=your_key_here
```

> **Important:** The `.env` file is gitignored and never committed. Each developer
> must set their own key.

### API endpoint

The Hermes profile is configured for the z.ai **Coding Plan** endpoint:

```
https://api.z.ai/api/coding/paas/v4
```

This endpoint is exclusive to the Coding Plan subscription. If you are on the
general plan, change `base_url` in `home/profiles/hermes/config.yaml.template`
to:

```
https://api.z.ai/api/paas/v4/
```

Then re-run `bash scripts/configure.sh` to regenerate the config.

---

## Step 5 — Verify

Run hermes and confirm it starts with GLM-5.1 and the Hermes Daimon identity:

```bash
hermes
```

You should see the Hermes Daimon system prompt and the `glm-5.1` model indicator.
No 401 errors means the key is valid and the correct endpoint is being used.

---

## MCP Servers

The Hermes Daimon has two MCP servers configured in `config.yaml.template`:

| Server | Purpose |
|--------|---------|
| `olympus` | Connects Hermes to the other Daimons via ACP protocol |
| `context7` | Fetches up-to-date library documentation for LLMs |

### context7 usage

Once running, add `use context7` to any prompt to pull live documentation:

```
use context7 — how does BubbleTea layout work in Go?
```

### Requirements

`context7` runs via `npx`. Make sure Node.js is installed:

```bash
node --version   # must be v18 or higher
```

Install Node.js if missing:

```bash
# Ubuntu / Debian
sudo apt install nodejs npm
```

---

## Quick reference

```bash
# 1. Set HERMES_HOME (add to ~/.bashrc)
export HERMES_HOME=/path/to/Aether-Agents/home

# 2. Generate configs
bash scripts/configure.sh

# 3. Set active profile
echo "hermes" > home/active_profile

# 4. Add your API key
echo "GLM_API_KEY=your_key" >> home/profiles/hermes/.env

# 5. Run
hermes
```

---

## Troubleshooting

**401 AuthenticationError from z.ai**
- The API key in `home/profiles/hermes/.env` is expired or incorrect
- Generate a new key at [z.ai](https://z.ai) and update `GLM_API_KEY`

**hermes starts with the wrong model**
- Check that `HERMES_HOME` points to `Aether-Agents/home` and not `~/.hermes`
- Check that `home/active_profile` contains `hermes`
- Run `hermes profile list` to see which profile is active

**context7 not found / npx error**
- Install Node.js: `sudo apt install nodejs npm`
- Verify: `node --version` (must be v18+)
