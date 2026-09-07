# Aether Agents — Website Content Architecture

Owner-review amendment: keep the eight-section sequence, but stop displaying its
internal numbers and drafting annotations in the page. The updated supporting Spanish
is in [COPY_REFINEMENT.md](COPY_REFINEMENT.md). The knowledge illustration now uses
SVG/HTML and GSAP lighting/exploration, preserving the approved classical visual accents;
authorship includes the linked @DarkArty07 handle. See [POLISH_PLAN.md](POLISH_PLAN.md).

## Status

Working content architecture for the public Aether Agents website. This document records
owner-approved website structure decisions and separates product presentation from product
documentation. It does not replace Aether's canonical design, specifications, capability
registry, or current documentation.

## Approved content decisions

### Language order

- Website content is authored **first in Spanish** and then adapted to **English**.
- Spanish is the source language while the website content is being designed.
- The English version must preserve meaning and product boundaries rather than becoming a
  loose marketing rewrite.
- The local candidate has a real ES/EN switch, preserving section anchors between `/`
  and `/en/`. Spanish is the default for this review candidate, not a deployed locale policy.

### Product website versus documentation

Aether uses two distinct reader surfaces:

1. **Product website / landing page** — a single-page, animated presentation of the product.
2. **Documentation** — a separate multi-page documentation surface for technical depth.

The one-page product site is not a substitute for documentation, and the documentation is
not expected to carry the visual or narrative burden of the product landing page.

### Product landing page responsibility

The one-page website should answer, in a concise visual narrative:

1. What is Aether?
2. Why does it exist?
3. How does its multi-agent architecture work?
4. How does intent become an executable contract?
5. How does autonomous execution, review and integration work?
6. How does project knowledge and role-scoped experience fit in?
7. How does Aether preserve visibility, safety and reversibility?
8. What foundations does Aether build on?
9. Who created the project and where is its open-source code?
10. Where can the reader continue: documentation and GitHub.

The landing page should remain editorial and concise. It must not reproduce the full CLI
reference, authority matrix, specification corpus, capability registry, patch ledger or
troubleshooting manual.

### Approved landing-page structure

The owner approved the eight-section grouping and reading order on 2026-09-06.
This is the content baseline for the next visual-design discussion.

| Order | Category in Spanish | Reader question |
| --- | --- | --- |
| 00 | Qué es Aether | ¿Qué estoy viendo y por qué me interesa? |
| 01 | Qué puedes desarrollar | ¿Qué le encargo y qué recibo? |
| 02 | Un equipo con responsabilidades claras | ¿Quién diseña, implementa y revisa? |
| 03 | Del objetivo al resultado | ¿Cómo se convierte una idea en una entrega? |
| 04 | Conocimiento que permanece | ¿Cómo reutiliza el contexto del proyecto? |
| 05 | Autonomía con límites y evidencia | ¿Qué puedo comprobar y controlar? |
| 06 | Abierto y configurable | ¿De qué depende y qué puedo elegir? |
| 07 | Autoría y código abierto | ¿Quién creó Aether y dónde puedo explorar o contribuir al código? |

The approved narrative introduces the product, possible assignments and deliverables
before explaining the team and its working method. Contracts, execution, review and
integration belong to one continuous account of delivery; technical depth remains in
the separate documentation surface.

Approval covers these categories, their grouping and their order. Sections 00 through 07
now also have approved content/visual decisions recorded in the homepage working document.
Final implementation
details such as exact animation timing, responsive behavior and frontend technology remain
separate decisions.

### Approved section details

- **00 / ORIGEN:** copy and hero treatment approved; uses the selected Morfeo/ether hero
  artwork and the approved foundation links.
- **01 / DESARROLLO:** copy approved, including the long-horizon/unattended block; visual
  approved as an animated greco-futurist orbital clock / astrolabe.
- **02 / EQUIPO:** copy approved literally; visual approved as an animated bidirectional
  role diagram with moving packets/pulses that can advance, branch, return and converge.
- **03 / PROCESO:** copy approved literally; visual approved as a distinct animated
  process pipeline showing intention, contract, decomposition, execution, review and
  integration, including visible return loops such as review back to execution.
- **04 / CONOCIMIENTO:** conceptual copy and Graphify explanation approved; visual approved
  as the supplied greco-futurist simplified knowledge-graph composition.
- **05 / CONTROL:** copy approved literally; intentionally text-led, with no strong visual
  asset or protagonist diagram. Use editorial typography and only subtle interface/motion
  details.
- **06 / FUNDAMENTOS:** copy approved literally, including Hermes Agent, GitHub Spec Kit,
  Graphify, provider/model flexibility and the Aether Router companion-project note.
  Intentionally text-led, with no strong visual asset; use restrained editorial composition
  instead of another hero-like illustration or a logo wall.
- **07 / AUTORÍA:** copy approved literally; presents Christopher Hernández Jiménez as
  creator of Aether Agents and states the project's MIT/open-source status, with GitHub and
  documentation links. Intentionally simple and text-led, with no new strong visual asset.

Sections 00–07 are now closed at the content/visual-concept level. Responsive behavior,
exact animation timing, final typography, implementation framework and language routing
remain separate implementation/design decisions.

### Approved section 01 visual

Section `01 / DESARROLLO` uses an animated greco-futurist orbital clock / astrolabe as
its principal visual metaphor for long-horizon unattended work. It is a frontend-built
visual rather than another photographic/image asset. Its animation conveys the passage
of time through slow orbital movement without displaying a concrete elapsed-time claim.
The approved concept pairs ancient Greek astronomical-instrument language with modern
computational instrumentation and may label the surrounding activity as `CREAR`,
`AMPLIAR` and `MEJORAR`, with `LONG HORIZON` / `UNATTENDED` at the center.

### Approved copy — section 01

The Spanish source copy for `01 / DESARROLLO` is now approved and recorded in
[Estrategia de contenido de la portada](HOMEPAGE_PROPOSAL.md). It includes the three
development modes `CREAR`, `AMPLIAR` and `MEJORAR`, the delivery statement, and a
separate `LONG HORIZON / UNATTENDED` block describing hours of autonomous work without
constant attention. Its orbital-clock visual is approved and implemented for local review.

### Approved section 00 copy and external references

The exact Spanish copy for section `00 / ORIGEN` is now approved and must be preserved
word-for-word as recorded in `HOMEPAGE_PROPOSAL.md`. The hero also carries low-emphasis
outbound references to Hermes Agent and GitHub Spec Kit as foundations, and Graphify as
optional knowledge integration. These references are links, not additional marketing
claims and not part of the hero's primary copy.

### Documentation responsibility

The separate documentation surface may contain the detailed technical material, including:

- overview and architecture;
- installation and prerequisites;
- setup and project initialization;
- concepts and role boundaries;
- Objective Contracts;
- execution, worktrees, review and lifecycle;
- project knowledge and work memory;
- CLI command reference;
- updates, rollback, uninstall and recovery;
- model/provider boundaries;
- Linux/WSL2 support;
- privacy and security;
- Hermes source-mode and downstream policy;
- troubleshooting and diagnostics;
- current limitations;
- contribution and release process.

The current repository `docs/` corpus remains the authoritative source for current-build
behavior. A future documentation website should publish or transform that content rather
than inventing a competing technical manual.

## Local candidate information architecture

The local candidate uses Astro static generation with these distinct routes:

```text
/
  Spanish one-page product website

/en/
  English adaptation of the same one-page product website

/docs/
  Multi-page technical documentation
```

The technical manual remains in its canonical English source language and is labeled
accordingly. The documentation index introduces it in Spanish; no parallel translation
of the manual is invented. No production domain or deployment is configured.

## Supporting landing-page analysis

[Estrategia de contenido de la portada](HOMEPAGE_PROPOSAL.md) develops the Spanish-first
analysis behind the approved eight-section structure and its literal Spanish copy.
The later section approvals supersede earlier suggestions. Only the selected 00 and 04
images are used; implementation choices are recorded in IMPLEMENTATION_PLAN.md.

## Open decisions

- Owner corrections to the completed local visual/interaction candidate.
- Approval of the English adaptation and final public default locale.
- Integration into main (explicitly not authorized by the implementation request).
- Hosting/domain and deployment strategy.

## Implementation authorization

After approving 00–07, the owner authorized autonomous planning and construction in the
isolated website worktree, with review at the end. This authorizes reversible local
frontend decisions but no merge, push, commit, publication, deployment or runtime change.
The implementation plan and verification record carry the selected technology and results.

## Decision log

### 2026-09-06 — Landing-page structure approved

The owner accepted recording the proposed eight categories and their order, then
explicitly deferred selecting their visual representations to the next discussion.
Spanish-first content and separate multi-page documentation remain unchanged.
