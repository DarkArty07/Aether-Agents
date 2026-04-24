PROJECTS_ROOT: /mnt/c/Users/chris/Desktop/DEVELOPERSPROJECTS/ — carpeta de proyectos de Christopher. Todos los proyectos van aquí.
§
ARTEMISA: POS minisuper. FastAPI+PostgreSQL+Tauri2+Svelte. Fase1=API, Fase2=MCP.
ZEUS LLM: Self-improving agent basado en Qwen 3.5 9B. Pipeline SFT→DPO→GRPO. Código/tool-calling como dominio con verificación automática. Christopher sabe ML conceptual pero es primer proyecto hands-on. PROJECTS_ROOT/Zeus LLM/.
§
z.ai Americas endpoint: https://open.zhipuai.ai/api/paas/v4 — China endpoint (open.bigmodel.cn) gives 401 for Americas keys.
§
AETHER: github.com/DarkArty07/Aether-Agents. Ruta /home/prometeo/Aether-Agents/ (branch dev). HERMES_HOME=$AETHER/home/profiles/hermes. Olympus MCP server en src/olympus/ (talk_to + discover via MCP stdio→ACP). 6 Daimons: hermes(orchestrator/GLM-5.1), ariadna(PM/kimi-k2.5), athena(security/kimi-k2.6), daedalus(UX/mimo-v2), etalides(research/minimax-m2.7), hefesto(dev/glm-5.1). Prometeo es asistente personal de Christopher, NO parte del framework. Todos personality:none. Delegation: qwen3.6-plus opencode-go.
§
CONTEXT7: @upstash/context7-mcp (NO @upstreamapi). Configurado en hermes config.yaml con npx -y @upstash/context7-mcp.
§
AETHER WORKFLOWS V2: Phase 1-2.3 DONE. Phase 2.3 (957d993): 6 new workflows replacing old 3. project-init(3n), feature(11n,3HITL), bug-fix(6n,1HITL), security-review(7n,1HITL), research(3n), refactor(6n,1HITL). HITL=interrupt()+Command. Phase 2.4 PENDING: testing.