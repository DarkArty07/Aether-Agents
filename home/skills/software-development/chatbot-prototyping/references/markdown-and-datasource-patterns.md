# Markdown Rendering & System-Prompt-as-DataSource Patterns

## Problem 1: Raw Markdown in Chat

LLM responses contain markdown (bold, headers, lists, code blocks). Without a markdown renderer, the user sees raw `**text**`, `### headers`, and `- list items` as literal text.

### Solution: react-markdown + manual CSS

```bash
npm install react-markdown
```

In `page.tsx`:
```typescript
import ReactMarkdown from "react-markdown";

// In message rendering:
<CardContent className="text-sm markdown-content">
  {message.role === "assistant" ? (
    <ReactMarkdown>{message.content}</ReactMarkdown>
  ) : (
    message.content
  )}
</CardContent>
```

In `globals.css` — manual CSS classes (NOT @tailwindcss/typography, which fails on Tailwind v4):
```css
.markdown-content h1, .markdown-content h2, .markdown-content h3,
.markdown-content h4 {
  font-weight: 600;
  margin-top: 1em;
  margin-bottom: 0.5em;
  line-height: 1.25;
}
.markdown-content h1 { font-size: 1.5rem; }
.markdown-content h2 { font-size: 1.25rem; }
.markdown-content h3 { font-size: 1.125rem; }
.markdown-content p { margin-bottom: 0.75em; }
.markdown-content ul, .markdown-content ol {
  padding-left: 1.5em;
  margin-bottom: 0.75em;
}
.markdown-content li { margin-bottom: 0.25em; }
.markdown-content ul { list-style-type: disc; }
.markdown-content ol { list-style-type: decimal; }
.markdown-content strong { font-weight: 600; }
.markdown-content em { font-style: italic; }
.markdown-content hr {
  margin: 1em 0;
  border-color: var(--color-border);
}
.markdown-content blockquote {
  border-left: 3px solid var(--color-muted-foreground);
  padding-left: 1em;
  color: var(--color-muted-foreground);
  margin-bottom: 0.75em;
}
.markdown-content code {
  background-color: var(--color-secondary);
  padding: 0.125rem 0.25rem;
  border-radius: 0.25rem;
  font-size: 0.875em;
}
.markdown-content pre {
  background-color: var(--color-secondary);
  padding: 0.75rem;
  border-radius: 0.5rem;
  overflow-x: auto;
  margin-bottom: 0.75em;
}
.markdown-content pre code {
  background: none;
  padding: 0;
}
```

### Why NOT @tailwindcss/typography?

Tailwind v4 changed the plugin system. The old `@plugin "@tailwindcss/typography";` directive in CSS fails with:
```
Can't resolve '@tailwindcss/typography' in '/path/to/src/app'
```
Even when the package is installed in node_modules. The manual CSS approach above works reliably and gives full control over styling.

## Problem 2: Tool Calling Doesn't Work with Text Protocol

When using `streamProtocol: "text"` (required for reliable rendering in ai@6.0.211), the LLM tool calling via `streamText({ tools: {...} })` may not trigger reliably. The model says "let me search for doctors" but never actually calls the tool.

### Solution: Embed Reference Data in the System Prompt

Instead of using tool calling, put the reference data directly in the system prompt as a structured text section:

```typescript
const result = streamText({
  model: llmgateway(cleanModel || "deepseek-v4-flash"),
  system: `# Asclepio — Asistente de Orientación en Salud para Viajeros

## Identity
You are Asclepio...

## FLUJO DE CONVERSACIÓN
### Paso 1: Bienvenida
...
### Paso 6: Canalización con doctores
Cuando el usuario necesite ver un médico, recomienda doctores de la base de datos abajo.

### Base de datos de doctores (REFERENCIA)
Cuando recomiendes un doctor, usa esta información. NO inventes doctores, usa solo estos:

CIUDAD DE MÉXICO (CDMX):
- Dr. Ricardo Mendoza García — Medicina General — Av. Insurgentes Sur 1234, Col. Roma — +52 55 2345 6789 — Lun-Vie 9:00-18:00
- Dra. Patricia Castillo Reyes — Cardiología — Polanco, Av. Reforma 250 — +52 55 3456 7890 — Lun-Vie 8:00-16:00
- Dr. Fernando Solís Cruz — Gastroenterología — Col. Condesa, Av. Amsterdam 150 — +52 55 4567 8901 — Lun-Vie 10:00-19:00

GUADALAJARA:
- Dr. Juan Martínez López — Medicina General — Av. Vallarta 1234, Col. Americana — +52 33 1234 5678 — Lun-Vie 9:00-18:00
- Dra. Daniela Cortés Muñoz — Gastroenterología — Av. López Mateos 4567, Col. Arcos — +52 33 7890 1234 — Lun-Vie 9:00-15:00

MONTERREY:
- Dra. Daniela Cortés Muñoz — Medicina General — Av. Roble 678, San Pedro Garza García — +52 81 1234 5678 — Lun-Vie 8:00-17:00
- Dra. Valeria Garza Villarreal — Gastroenterología — Av. Hidalgo 500, Col. Obispado — +52 81 6789 0123 — Lun-Vie 8:00-15:00

Cuando el usuario pida un doctor, presenta los datos en formato claro:
Nombre, especialidad, dirección, teléfono, horario.
Si no hay un doctor de la especialidad solicitada en la ciudad del usuario, ofrece Medicina General como alternativa.`,
  messages,
});

return result.toTextStreamResponse();
```

### Tradeoffs

| Aspect | Tool Calling | System Prompt Data |
|--------|-------------|-------------------|
| Dynamic queries | Yes (filtered at runtime) | No (LLM reads all data) |
| Context window | Minimal (only query results) | Larger (all data in prompt) |
| Reliability | Depends on protocol + SDK version | Always works |
| Setup complexity | Tools + zod + execute functions | Just text in template literal |
| Data size limit | Unlimited (DB-backed) | ~200 entries before token cost matters |

### When to use which

- **System prompt data**: prototypes with <200 entries, static data, need reliability
- **Tool calling**: production, large datasets, dynamic queries, when SDK version supports it
- **Hybrid**: use system prompt for common data (top 3 cities), tool calling for the rest

### Generating Fictitious Data at Scale

For a prototype covering many locations (e.g., all 32 Mexican states), delegate data generation to Hefesto with clear specs:

- Total count target (e.g., 120-150 entries)
- Fields per entry (name, specialty, city, state, address, phone, schedule, rating, languages)
- Coverage requirements (e.g., "top 10 cities must have all 8 specialties")
- Realistic formatting (proper phone ladas, real street names, neighborhood names)
- Sequential IDs
- Mix of Dr./Dra. (60/40 split)
- Proper Spanish accents (á, é, í, ó, ú, ñ)

For the system prompt specifically, condense to one-liners per doctor to save tokens:
```
- Dr. Name — Specialty — Address — Phone — Schedule
```
Rather than full JSON objects.
