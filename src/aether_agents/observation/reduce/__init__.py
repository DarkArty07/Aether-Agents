"""Deterministic ingestion, reconciliation, and reduction.

Reduction is pure with respect to its input: it never appends to, rewrites, migrates, or
truncates a journal segment (OBS-D-025, OBS-FR-080). A reducer that writes into its own
input makes replay history-dependent and can recursively duplicate diagnostics.
"""

from __future__ import annotations
