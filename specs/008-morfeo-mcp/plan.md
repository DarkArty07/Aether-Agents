# Plan

1. RC9 reads schema 4 and schema 5, emits schema 4, and installs `hermes.extras`
   from the fork lock when a target declares them.
2. After RC9 is on `main`, RC10 emits schema 5 with `hermes.extras: ["mcp"]`
   and adds the Morfeo MCP runtime and `aether mcp morfeo serve`.
3. Do not modify the Hermes fork unless an interface at the pinned commit is
   shown to be insufficient.
