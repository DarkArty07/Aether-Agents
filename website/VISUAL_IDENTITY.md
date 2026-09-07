# Aether Agents — Visual Identity System

**Status:** working visual identity for the public website
**Last updated:** 2026-09-06

This document records visual decisions explicitly approved for the Aether Agents
website. It is the working reference for the site's art direction; suggestions and
experiments are not considered approved until they are added here as decisions.

## 1. Approved visual direction

The Aether Agents website uses an **editorial tech-noir / retrofuturist** visual
language, based on the references selected by the owner.

The intended character is:

- dark and sophisticated rather than conventional SaaS;
- editorial and asymmetric rather than card-grid driven;
- technological, archival and computational;
- compatible with monochrome or heavily processed imagery;
- suitable for dithering, halftone, bitmap, CRT/noise and other low-fidelity digital
  treatments when individual compositions are defined;
- presented as a **single-page / one-page website with animation**.

The reference material defines the visual language, not production assets to copy.

## 2. Color system — Catppuccin Mocha

**Decision:** Catppuccin **Mocha** is the canonical color palette for the website and
the project's public visual identity.

### Primary project accent

| Token | Hex | Role |
| --- | --- | --- |
| **Mauve** | **`#CBA6F7`** | Primary Aether accent / signature purple |

Mauve is the characteristic Aether purple and should be treated as the principal
brand accent rather than one accent among many.

### Core website neutrals

| Token | Hex | Intended role |
| --- | --- | --- |
| Crust | `#11111B` | Deepest background |
| Mantle | `#181825` | Secondary dark background |
| Base | `#1E1E2E` | Main dark surface |
| Surface 0 | `#313244` | Raised surfaces / subtle divisions |
| Surface 1 | `#45475A` | Borders / stronger divisions |
| Surface 2 | `#585B70` | Secondary structural elements |
| Overlay 0 | `#6C7086` | Muted interface detail |
| Overlay 1 | `#7F849C` | Metadata / subdued labels |
| Overlay 2 | `#9399B2` | Secondary labels |
| Subtext 0 | `#A6ADC8` | Secondary text |
| Subtext 1 | `#BAC2DE` | Strong secondary text |
| Text | `#CDD6F4` | Primary text |

### Catppuccin Mocha accents

The remaining Mocha accents belong to the project palette and may be used when the
composition or semantic purpose warrants them.

| Token | Hex |
| --- | --- |
| Rosewater | `#F5E0DC` |
| Flamingo | `#F2CDCD` |
| Pink | `#F5C2E7` |
| Mauve | `#CBA6F7` |
| Red | `#F38BA8` |
| Maroon | `#EBA0AC` |
| Peach | `#FAB387` |
| Yellow | `#F9E2AF` |
| Green | `#A6E3A1` |
| Teal | `#94E2D5` |
| Sky | `#89DCEB` |
| Sapphire | `#74C7EC` |
| Blue | `#89B4FA` |
| Lavender | `#B4BEFE` |

### Color hierarchy

The palette is not intended to become a rainbow interface. The working hierarchy is:

1. Catppuccin's dark neutrals establish the environment.
2. `Text` and the subtext tones carry typography and information.
3. `Mauve` is the dominant Aether identity accent.
4. Other Catppuccin accents remain available for controlled secondary or semantic use.

This preserves a predominantly dark editorial presentation while making the project
recognizably Catppuccin Mocha rather than generic black-and-white tech-noir.

## 3. Approved site format

- One continuous **one-page / mono-page** public website.
- Motion and scroll-based animation are part of the intended experience.
- The section-specific motion concepts are approved. Exact timing and technical choices
  are implementation decisions of the local review candidate.

The approved eight-section content sequence is maintained in
[Website Content Architecture](CONTENT_ARCHITECTURE.md). Later approvals selected the
Morfeo/ether hero, orbital clock, bidirectional role diagram, process with rework and
the simplified Graphify illustration. Sections 05–07 are intentionally text-led.

## 4. Greek identity and selected artwork

The owner clarified that Aether has a Greek identity with modern elements. Ether is
used as the brand metaphor of creative origin; Morfeo has a divine/sculptural visual
presence. These are brand concepts, not claims about historical mythology.

Only two owner-provided raster artworks are selected for this candidate: Morfeo
emerging from ether (00) and the simplified knowledge graph (04). Do not use the
unselected control-room, dossier or cosmic-background images. The original PNGs and
their hashes are documented in [assets/README.md](assets/README.md).

## 5. Local implementation choices — subject to owner review

- Display: self-hosted Barlow Condensed, 600 and 700.
- Body: self-hosted Space Grotesk, 400 and 500.
- Technical labels: self-hosted IBM Plex Mono, 400.
- Large left-aligned hero typography and the selected figure to the right; mobile
  preserves the face above the name and description rather than hiding it.
- Native SVG orbital clock and role/process diagrams. Slow orbital motion, packets
  that branch/return/wait, and a review-to-execution loop. No invented measured durations.
- Restrained graph-image pulse; all important explanations remain actual HTML text.
- Responsive editorial grids; sticky navigation; reversible ES/EN routes; global pause
  with persisted preference and system reduced-motion support.
- Astro static output; no frontend framework hydration or external animation library.

The owner's final corrections, production domain, deployment and integration remain open.

## 6. Decision log

### 2026-09-06

- Approved the editorial tech-noir / retrofuturist direction from the supplied visual
  references.
- Approved a single-page animated website.
- Approved **Catppuccin Mocha** as the project's website color system.
- Approved **Mauve `#CBA6F7`** as Aether's primary signature accent.
