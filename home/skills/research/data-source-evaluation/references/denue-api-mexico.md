# DENUE API (INEGI) — Complete Reference

## Overview
DENUE (Directorio Estadístico Nacional de Unidades Económicas) is Mexico's official business directory. Free, no rate limit documented, covers 6M+ establishments nationwide from Censos Económicos 2024.

- **URL base**: `https://www.inegi.org.mx/app/api/denue/v1/consulta`
- **Token**: Free, instant at `https://www.inegi.org.mx/app/api/denue/v1/tokenVerify.aspx`
- **Format**: GET with positional URL parameters, returns JSON array
- **Rate limit**: NOT documented — implement backoff from day one

## 7 API Methods

### 1. Cuantificar — "How many?"
Count establishments by activity + area + size. Best for TAM estimation.
```
Endpoint: /Cuantificar/{actividad}/{area_geografica}/{estrato}/{token}
Parameters:
  actividad: SCIAN code (0=all, 54=sector, 541510=class)
  area_geografica: entity code (0=per-entity breakdown, 09=CDMX)
  estrato: 0-7 (0=all, 4=31-50 employees)
```

### 2. Buscar — "What's near here?"
Free text search by keyword + lat/lon + radius (max 5,000m).
```
Endpoint: /Buscar/{condicion}/{lat},{lon}/{metros}/{token}
```

### 3. Ficha — "Details for this one"
Single establishment by ID. Returns FEWER fields than BuscarAreaActEstr.
```
Endpoint: /Ficha/{id_establecimiento}/{token}
```

### 4. Nombre — "Does this company exist?"
Search by name/razón social, optionally filtered by entity. Paginated.
```
Endpoint: /Nombre/{nombre}/{entidad}/{registro_inicial}/{registro_final}/{token}
```

### 5. BuscarEntidad — "Search this in a whole state"
Like Buscar but without radius restriction. Paginated.
```
Endpoint: /BuscarEntidad/{condicion}/{entidad}/{registro_inicial}/{registro_final}/{token}
```

### 6. BuscarAreaAct — "Filter by industry + location"
Systematic scanning by geography + full SCIAN taxonomy. Paginated.
```
Endpoint: /BuscarAreaAct/{entidad}/{municipio}/{localidad}/{ageb}/{manzana}/
          {sector}/{subsector}/{rama}/{clase}/{nombre}/
          {registro_inicial}/{registro_final}/{id_establecimiento}/{token}
```

### 7. BuscarAreaActEstr — "Filter by industry + location + SIZE"
THE MOST POWERFUL METHOD. Same as BuscarAreaAct but adds company size filter.
```
Endpoint: /BuscarAreaActEstr/{entidad}/{municipio}/{localidad}/{ageb}/{manzana}/
          {sector}/{subsector}/{rama}/{clase}/{nombre}/
          {registro_inicial}/{registro_final}/{id_establecimiento}/{estrato}/{token}
```

## Estrato (Company Size) Codes
| Value | Range |
|-------|-------|
| 0 | All sizes |
| 1 | 0-5 employees |
| 2 | 6-10 employees |
| 3 | 11-30 employees |
| 4 | 31-50 employees |
| 5 | 51-100 employees |
| 6 | 101-250 employees |
| 7 | 251+ employees |

## Data Quality — Measured Fill Rates

### IT Services (SCIAN 541510), CDMX, n=10
| Field | Fill Rate |
|-------|-----------|
| Nombre | 100% |
| Dirección completa | 100% |
| Clase_actividad | 100% |
| Estrato | 100% |
| Correo_e | **70%** |
| Sitio_internet | **80%** |
| Telefono | **10%** |

### IT Services (SCIAN 541510), EdoMex, n=5
| Field | Fill Rate |
|-------|-----------|
| Correo_e | 40% |
| Sitio_internet | 40% |
| Telefono | 20% |

### Key Finding
Email fill rate (~70% for IT/CDMX) is MUCH higher than initially assumed. Website fill rate ~80% provides a domain for waterfall enrichment. Phone fill rate is consistently poor (~10%).

## Fields Returned (BuscarAreaActEstr — 34 fields)
- **Identity**: CLEE, Id, Nombre, Razon_social
- **Classification**: Clase_actividad, Estrato, SCIAN codes (Sector, Subsector, Rama, Subrama, Clase)
- **Address**: Tipo_vialidad, Calle, Num_Exterior, Num_Interior, Colonia, CP, Ubicacion
- **Coordinates**: Longitud, Latitud
- **Contact**: Telefono, Correo_e, Sitio_internet
- **Metadata**: AGEB, Manzana, Fecha_Alta, tipo_corredor_industrial, nom_corredor_industrial, AreaGeo, Tipo_Asentamiento, EDIFICIO_PISO

## Geographic Coverage — IT Services (541510)
| Entity | Count |
|--------|-------|
| CDMX (09) | 685 |
| Nuevo León (19) | 338 |
| Jalisco (14) | 265 |
| EdoMex (15) | 190 |
| Puebla (21) | 143 |
| Baja California (02) | 116 |
| Guanajuato (11) | 114 |
| National total | ~2,700+ |

## SCIAN Codes — Useful for B2B Prospecting
| Code | Industry |
|------|----------|
| 54 | Professional, Scientific, Technical Services |
| 541 | Professional Services |
| 5415 | Computer Systems Design |
| 541510 | IT Services / Computer Systems Design |
| 51 | Information Media |
| 512 | Film & Video Industries |
| 5121 | Film & Video |
| 512130 | Film Exhibition (Cinemas) |
| 72 | Accommodation & Food Services |
| 722 | Food Services |
| 46 | Retail Trade |
| 31-33 | Manufacturing |

## Integration Pattern
DENUE works best as a DISCOVERY layer:
1. Cuantificar → dimension TAM by sector/geo/size
2. BuscarAreaActEstr → systematic sweep by SCIAN + entity + size
3. Extract Correo_e + Sitio_internet from enriched records
4. Feed domains into waterfall enrichment (Hunter.io, scraping, LLM)

## Limitations
- Phone numbers: ~10% fill rate, often outdated
- No personal contacts (no CEO/CTO names, no LinkedIn URLs)
- No technographics (doesn't know if they use AWS, Salesforce, etc.)
- Freshness: depends on census cycles; PyMEs may have stale data
- Ficha returns FEWER fields than BuscarAreaActEstr (lacks SCIAN breakdown, AGEB, Fecha_Alta)
- Cuantificar with area=0 returns per-entity breakdown, not national total (need to sum)
