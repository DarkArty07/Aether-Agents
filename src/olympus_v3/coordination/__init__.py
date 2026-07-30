"""Public API for the maintained coordination kernel foundations."""

# Re-exporting each maintained module's declared ``__all__`` preserves the
# package-level compatibility surface while keeping the retired modules absent.
# ruff: noqa: F403

from . import closure as _closure
from . import contracts as _contracts
from . import effects as _effects
from . import kernel_dispatcher as _kernel_dispatcher
from . import leases as _leases
from . import ledger as _ledger
from . import olympus_adapter as _olympus_adapter
from . import principal as _principal
from . import projections as _projections
from . import review as _review
from .closure import *
from .contracts import *
from .effects import *
from .kernel_dispatcher import *
from .leases import *
from .ledger import *
from .olympus_adapter import *
from .principal import *
from .projections import *
from .review import *

__all__ = sorted(
    {
        *_closure.__all__,
        *_contracts.__all__,
        *_effects.__all__,
        *_kernel_dispatcher.__all__,
        *_leases.__all__,
        *_ledger.__all__,
        *_olympus_adapter.__all__,
        *_principal.__all__,
        *_projections.__all__,
        *_review.__all__,
    }
)
