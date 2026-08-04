"""Temporary Olympus compatibility facade for the retiring kernel."""

# Re-exporting each maintained module's declared ``__all__`` preserves the
# package-level compatibility surface while keeping the retired modules absent.
# ruff: noqa: F403

import aether_agents as _aether
from aether_agents import *

from . import kernel_dispatcher as _kernel_dispatcher
from . import leases as _leases
from . import ledger as _ledger
from . import olympus_adapter as _olympus_adapter
from . import projections as _projections
from .kernel_dispatcher import *
from .leases import *
from .ledger import *
from .olympus_adapter import *
from .projections import *

__all__ = sorted(
    {
        *_aether.__all__,
        *_kernel_dispatcher.__all__,
        *_leases.__all__,
        *_ledger.__all__,
        *_olympus_adapter.__all__,
        *_projections.__all__,
    }
)
