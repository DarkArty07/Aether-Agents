# MCP tool-surface evaluation

The current 15 tools are the frozen compatibility baseline. Do not rename, remove or merge them without a preregistered comparison and explicit owner decision.

Evaluate representative cold-start cases for:

- correct first tool and sequence;
- correct identity and effect handling;
- schema/typed-denial rate;
- unnecessary discovery or description calls;
- task completion and cleanup evidence;
- time, calls, tokens and reported cost (unknown is not zero);
- unsafe retries, hidden fallbacks or authority expansion.

Keep model, prompt, initial context, provider and task fixtures equivalent across comparisons. The candidate cannot edit its own evaluator or acceptance thresholds. Tool-description improvements may be tested without dispatch; model-backed cases require a separate execution/spend gate.
