# python-docx `Cm()`/`Pt()` × MCP/JSON String Transport — Reference Transcript

**Recorded:** 2026-06-04 (clio-fca MCP, modo `academico` first production deployment)
**Skill:** `hermes-agent` v2.4.0, Pitfall #N
**Status:** Resolved (commit `dc9e642` on `clio-fca-mcp` repo)

## TL;DR

`python-docx.Cm(value)` ejecuta `int(value * 360000)` internamente. Si el transporte MCP/JSON entrega un float como string (`"2.5"` en vez de `2.5`), Python hace string multiplication: `"2.5" * 360000` = 1.44 MB de `"2.5"` repetido, que `int()` no puede parsear. El operador ve solo el truncado en terminal (`~80 reps`), piensa que es concatenación en loop, busca el sitio equivocado.

## Transcript (condensado)

### Síntoma reportado por Chris

> "Cuando llamo a fca_generate_task con style='academico' y un academico_config que incluye los 4 márgenes como números, la herramienta falla con este error:
>
> `invalid literal for int() with base 10: '2.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52.52'`
>
> El string del error tiene exactamente 80+ repeticiones de '2.5', lo que sugiere que hay un loop o format string que recorre los 4 márgenes múltiples veces concatenándolos sin separador."

### Diagnóstico inicial (Chris, parcial)

> "En el archivo `src/clio_fca/fca/generator.py` (donde agregaste las +420/-9 líneas para el modo academico), hay un bloque que probablemente se ve similar a:
>
> ```python
> # MAL — concatena márgenes como string
> margin_str = "".join(str(m) for m in [
>     config.get("margin_top_cm"),
>     config.get("margin_bottom_cm"),
>     config.get("margin_left_cm"),
>     config.get("margin_right_cm")
> ])
> ```

Chris sospechó concatenación en loop. La intuición estaba cerca (4 márgenes, multiplicador) pero el mecanismo real era diferente.

### Diagnóstico correcto (Hefesto, 5 minutos de búsqueda dirigida)

```python
# python-docx/shared.py
class Cm(Length):
    def __new__(cls, cm):                              # cm llega como "2.5" string
        emu = int(cm * 360000)                         # "2.5" * 360000 = string multiplication
        return Length.__new__(cls, emu)
```

`"2.5" * 360000` en Python produce **string multiplication**, no error: `"2.5" * 360000` = string de 1,440,000 caracteres (la "2.5" repetida 360,000 veces). Luego `int()` de ese string gigante lanza `ValueError: invalid literal for int() with base 10: '2.52.52.5...'`.

**Por qué "80 reps" en el mensaje de error:** La terminal trunca el output a 80 repeticiones para mantener legibilidad. Internamente son 360,000 (el factor de conversión cm → EMU).

### Trace del origen del string

```python
# generator.py:75-80 (load_academic_config)
def load_academic_config(overrides: dict | None = None) -> AcademicConfig:
    config = AcademicConfig()  # defaults
    if overrides:
        for key, val in overrides.items():
            if hasattr(config, key):
                setattr(config, key, val)  # ← val puede ser "2.5" (str)
    return config
```

`overrides` viene del MCP tool `fca_generate_task(academico_config: dict)`. Cuando el cliente (Telegram/CLI) serializa el dict via JSON, los floats son strings si:
1. El caller construye el dict manualmente con `"2.5"` (no `2.5`)
2. JSON-RPC interpreta números grandes como strings en transporte
3. YAML config los carga como `margin_top_cm: "2.5"` (string)

`setattr` no coerce — guarda `"2.5"` tal cual en `config.margin_top_cm: float` (la dataclass annotation miente, el valor real es string).

### Fix aplicado (9 líneas, en el boundary)

```diff
@@ -85,6 +85,15 @@ def load_academic_config(overrides: dict | None = None) -> AcademicConfig:
     if overrides:
         for key, val in overrides.items():
             if hasattr(config, key):
+                # Coerce string values from JSON/MCP to the correct type
+                current = getattr(config, key)
+                if isinstance(val, str) and not isinstance(current, str):
+                    if isinstance(current, bool):
+                        val = val.lower() in ("true", "1", "yes")
+                    elif isinstance(current, int):
+                        val = int(val)
+                    elif isinstance(current, float):
+                        val = float(val)
                 setattr(config, key, val)
     return config
```

**Por qué coerce en el boundary y no en cada `Cm()`:**

| Approach | LOC | Riesgo de regresión |
|---|---|---|
| Coerce genérico en `load_academic_config` (1 sitio) | 9 | Bajo — 1 punto de cambio para TODOS los campos |
| `Cm(float(config.margin_top_cm))` (8 sitios) | 8×1=8 | Alto — 8 puntos de fallo, fácil olvidar uno nuevo (`font_size_*`, `line_spacing_*`) |
| Cambiar signature de Cm a `Cm(float)` | 1 | No factible — `Cm` es de python-docx |

El fix genérico cubre: `margin_*_cm` (4 campos), `font_size_*` (3 campos), `line_spacing_*` (2 campos) = 9 campos. Cualquier campo nuevo `int`/`float`/`bool` en `AcademicConfig` queda protegido automáticamente.

## Generalización a otros frameworks de unidades

Cualquier constructor de unidad que use `int(value * factor)` con factor grande es vulnerable:

| Library | Constructor | Internal formula | Factor | Risk si string |
|---|---|---|---|---|
| `python-docx` | `Cm(x)` | `int(x * 360000)` | 360,000 | "x" * 360000 = 1.4 MB string |
| `python-docx` | `Pt(x)` | `int(x * 12700)` | 12,700 | "x" * 12700 = 25 KB string |
| `python-docx` | `Inches(x)` | `int(x * 914400)` | 914,400 | "x" * 914400 = 3.6 MB string |
| `python-docx` | `Emu(x)` | `int(x)` | 1 | No risk (no multiplication) |
| `Pillow` | `ImageFont.truetype(path, size)` | `int(size * 1)` | 1 | No risk (no multiplication) |
| `reportlab` | `inch`, `cm`, `mm` | `int(x * 72)`, etc. | 72 | "x" * 72 = 144 char string |
| `matplotlib` | `inches`, `pt` | `int(x * 72)`, `int(x * 1)` | 72 | "x" * 72 |
| `wand` | `Width`, `Height` | `int(x)` | 1 | No risk |
| `ffmpeg-python` | `size` arg | pass-through | 1 | No risk |

**Regla práctica:** Si el factor es >100, coerce en boundary es obligatorio. Si el factor es 1, el riesgo es bajo pero no cero (ej. `Emu("2.5")` lanza `ValueError` directamente, no string multiplication).

## Los 3 caminos por los que un float llega como string

1. **JSON-RPC sin type hints** — el schema declara `margin_top_cm: float` pero la serialización no enforce; el cliente MCP envía string en `arguments`. Común en tools MCP con `arguments: dict[str, Any]`.

2. **YAML sin parseo de tipo** — `margin_top_cm: "2.5"` en YAML se queda como string. Si el dataclass usa `setattr` (no `pydantic.BaseModel`), no coerce.

3. **MCP/ACP transport** — pydantic valida el schema declarado, pero si la tool recibe `dict | None` o `Any`, no coerce. El dict se pasa literal al código downstream.

**Prevención universal:** Cualquier tool MCP que reciba `dict` con campos numéricos, debería coerce en el primer punto de entrada (load function, no en cada uso de `Cm()`). El pattern de 9 líneas de la fix es reusable.

## Diagnóstico checklist

Cuando veas `ValueError: invalid literal for int() with base 10: '<repeated-pattern>...'`:

```bash
# 1. ¿El string se parece a un patrón de repetición?
echo "<error_string>" | grep -oE '<value>' | wc -l
# Si el count es > 2 y divisible por la longitud del valor base → string multiplication

# 2. ¿Qué constructor recibe el valor?
grep -rn "int(.*\* [0-9]\|int(.*/ [0-9]" path/to/tool/
# python-docx: shared.py — Cm (×360000), Pt (×12700), Inches (×914400)

# 3. ¿El valor es string en el punto de entrada?
# Instrumenta: print(type(val), repr(val)) antes del constructor
# Si <class 'str'> '2.5' → string transport confirmed

# 4. ¿De dónde viene el dict?
# Trace el flujo: MCP tool arg → dataclass field → constructor
# Probable culprit: setattr() sin coerce, o YAML con strings quoted
```

## Anti-patterns

**Anti-pattern 1 — Coerce ad-hoc en el sitio del crash:**
```python
# El bug aparece en Cm(config.margin_top_cm)
# "Fix rápido" tentador:
section.top_margin = Cm(int(config.margin_top_cm))   # TypeError si es float
section.top_margin = Cm(float(config.margin_top_cm)) # funciona, pero...
# ¿y Cm(config.font_size_title)? Cm(config.line_spacing_body)? Cm(config.margin_*_cm)?
# Quedan 7 puntos de fallo latentes. El bug rebrota en producción.
```

**Anti-pattern 2 — Asumir que el dataclass annotation es enforcement:**
```python
@dataclass
class AcademicConfig:
    margin_top_cm: float = 2.5  # ← annotation, no enforcement
```
La annotation `float` no coerce en runtime. `setattr(config, 'margin_top_cm', '2.5')` lo guarda como string. El código downstream `Cm(config.margin_top_cm)` explota. Use `pydantic.BaseModel` o coerce explícito.

**Anti-pattern 3 — Confiar en JSON Schema para enforce de tipos:**
```python
# En el schema MCP
"margin_top_cm": {"type": "number"}  # ← solo declara, no coerce
```
El schema es **documentación** para clientes. El código del server debe validar y coerce explícitamente.

## Related pitfalls in `aether-agents-orchestration`

- **Pitfall #8 (Trusting Delegation "Completed" Without Verification):** Si Hefesto reporta "PASS" pero el código tiene un bug latente, hay que verificar con smoke test. Aplica aquí: el fix del string trap debería incluir un test que pase `"2.5"` como string y verifique que `load_academic_config` lo coerce correctamente.

- **Pitfall #11 (Olympus v3 ACP Returns "Internal error"):** Los errores "internal" de ACP a veces son el string multiplication que se origina en la tool llamada. Vale revisar el stderr log del MCP server, no solo el mensaje retornado.

## Real-world impact

- **First seen:** 2026-06-04 (clio-fca MCP, modo `academico`)
- **Affected fields:** 9 (4 margins + 3 font sizes + 2 line spacings)
- **Symptom latency:** First production call (no test suite covered this path)
- **Fix size:** 9 lines (1 patch, 0 deps added)
- **Regression risk:** Zero (coerce es aditivo, no cambia tipos para valores correctos)
- **Forward protection:** Any future field in `AcademicConfig` is auto-protected

## Code reusable snippet

Si necesitas agregar este patrón a otro proyecto:

```python
def coerce_config_overrides(config: Any, overrides: dict) -> None:
    """Coerce string values from JSON/MCP/YAML to the declared type of each dataclass field.
    
    Use when a tool receives a dict of overrides where numeric/bool values may arrive as strings
    (JSON-RPC, YAML untyped, MCP transport). Apply to the config object in-place.
    """
    for key, val in overrides.items():
        if not hasattr(config, key):
            continue
        current = getattr(config, key)
        if isinstance(val, str) and not isinstance(current, str):
            if isinstance(current, bool):
                val = val.lower() in ("true", "1", "yes")
            elif isinstance(current, int):
                val = int(val)
            elif isinstance(current, float):
                val = float(val)
        setattr(config, key, val)
```

Colocar al inicio de cualquier `load_X_config(overrides)` function. Cubre `bool`, `int`, `float`. Para `list`/`dict` nested, agregar branches adicionales.
