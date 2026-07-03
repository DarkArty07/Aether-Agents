# Presentation Prompt Template (Condensed)

Target: ~150 lines, ~7KB. NOT 87KB with verbatim transcripts.

## Structure

```
# PROMPT PARA PRESENTACIÓN — [PROJECT NAME]

Eres un agente generador de presentaciones. Crea una presentación PowerPoint (.pptx) ejecutiva...

## 1. QUÉ ES [PROJECT] — 1 paragraph

## 2. POR QUÉ UN BENCHMARK — 1 paragraph

## 3. METODOLOGÍA
- Scoring eliminatorio (explain)
- Criterios (table)
- Casos (numbered list, 1-2 lines each)
- Agente-paciente mechanism (2 sentences)
- Juez (1 sentence)

## 4. ARQUITECTURA — key components + flow diagram description

## 5. DECISIONES CLAVE — numbered list with 1-line justifications

## 6. [SPECIAL TOPIC] — e.g., SOUL.md adjustment, before/after table

## 7. LOS N MODELOS — price table

## 8. RESULTADOS — [MODEL NAME]
- Score table (columns: caso, run, score, etapa, descalif, hallazgo)
- Descalificaciones: 1-2 sentences each
- Fortalezas/Debilidades: bullet lists

## 9. ANÁLISIS
- Hallazgo principal (2-3 sentences)
- El benchmark funciona (evidence)
- Veredicto (1 sentence)
- Proyección costo

## 10. RECOMENDACIÓN — authorize full run

## INSTRUCCIONES PRESENTACIÓN — slide structure, format: PowerPoint (.pptx)
```

## Anti-Pattern

DO NOT include:
- Verbatim transcripts (6 × 5-12KB each)
- Full JSON scores (6 × 2-3KB each)
- Complete SOUL.md
- Complete cases.py
- Raw logs

The prompt is a BRIEFING DOCUMENT for an external agent — it needs SYNTHESIS, not raw data.

## Condensation Workflow

1. Read results.csv + scores → extract key data
2. Write analysis (findings, opinions, verdict)
3. Condense everything into ~150 lines
4. Verify: file should be ~7KB, not 87KB
5. If >200 lines: cut more. Target the STORY, not the evidence.
