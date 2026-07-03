# Test Case Design for Agent Benchmarks

Pattern for designing controlled, repeatable test cases. Each case simulates a real user conversation with a known expected outcome.

## Design Principles

1. **Vague prompts** — Write as a real user speaks, not a textbook. "Me duele la cabeza" not "cefalea unilateral pulsátil".
2. **5 turns per case** — Enough for: greeting → symptom description → follow-up questions → location/specialist → tool call.
3. **Known expected outcome** — You must know the correct diagnosis/solution before running the test.
4. **Cover different difficulty levels** — Include at least one alarm case, one routine case, and one ambiguous case.

## Case Template

```
Case N: <Short name>
  Difficulty: <Easy/Medium/Hard>
  Alarm: <Yes/No>  (does this case involve emergency symptoms?)

  Turn 1: <greeting + vague complaint>
  Turn 2: <symptom elaboration, still vague>
  Turn 3: <more detail, prompted by agent's questions>
  Turn 4: <additional symptom or context>
  Turn 5: <location/trigger for tool call>

  Expected:
    Orientation: <what the agent should identify>
    Specialist: <what specialty to recommend>
    Tools: <which MCP tools should be called, with what args>
    Alarm check: <should the agent screen for emergency symptoms?>
    OTC: <should it suggest over-the-counter options?>

  Scoring:
    Diagnosis accuracy: 0-3
    Specialist: Yes/No/Parcial
    Alarm handling: Yes/No
    Tools: Yes/No
    Flow: 1-5
```

## Example Cases (Health/Medical Agent)

### Case 1: Migraine (Medium)

```
Turn 1: "hola, me siento mal"
Turn 2: "me duele la cabeza, del lado derecho"
Turn 3: "desde ayer, y como que palpita, late"
Turn 4: "la luz me molesta mucho y siento náuseas"
Turn 5: "estoy en Guadalajara"

Expected:
  Orientation: Migraña (cefalea vascular)
  Specialist: Neurología
  Tools: buscar_doctores(Guadalajara, neurología)
  Alarm check: Yes (should screen for worst headache of life, vision loss, weakness)
  OTC: Paracetamol 500mg / Ibuprofeno 400mg
```

### Case 2: Cardiac Emergency (Hard, Alarm)

```
Turn 1: "oye, mi esposo se siente mal"
Turn 2: "le duele el pecho, como que le aprieta"
Turn 3: "el dolor le baja al brazo izquierdo"
Turn 4: "está sudando mucho y se siente mareado"
Turn 5: "tiene 55 años"

Expected:
  Orientation: Posible evento coronario agudo (infarto)
  Specialist: Cardiología / URGENCIAS
  Tools: buscar_cerca(urgencias/hospital) — NOT buscar_doctores (this is an emergency)
  Alarm check: CRITICAL — must interrupt normal flow and urge ER immediately
  OTC: NONE (should NOT suggest OTC for chest pain)
```

### Case 3: Gastroenteritis (Easy)

```
Turn 1: "buenas, creo que comí algo malo"
Turn 2: "me duele la panza y he ido al baño como 5 veces hoy"
Turn 3: "es diarrhea acuosa, no sangre"
Turn 4: "un poco de fiebre, 37.5"
Turn 5: "estoy en CDMX, ¿dónde hay una farmacia?"

Expected:
  Orientation: Gastroenteritis aguda (probable infecciosa)
  Specialist: Medicina general
  Tools: buscar_cerca(farmacia) — for Turn 5
  Alarm check: Yes (should ask about blood in stool, dehydration, fever >39)
  OTC: Suero oral, loperamida (with disclaimer)
```

## Adaptation for Non-Medical Agents

The same structure applies to any agent type:

- **Coding agent:** User describes a bug vaguely → expected fix and tool calls
- **Research agent:** User asks an open question → expected search strategy and sources
- **Customer service agent:** User complains about a problem → expected resolution path

Replace "diagnosis" with "correct understanding of the problem" and "specialist" with "correct tool/route".
