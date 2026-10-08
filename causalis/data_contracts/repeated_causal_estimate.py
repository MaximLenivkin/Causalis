"""Scalar inference with explicitly retained cross-fitting repetitions."""
from typing import List

from .causal_estimate import CausalEstimate


class RepeatedCausalEstimate(CausalEstimate):
    """Median aggregate and detached single-partition estimates.

    The primary diagnostic_data is None. Use repetition_estimates for each
    partition's diagnostics; no single influence function describes a median.
    Relative effects are aggregated separately and can be undefined.
    """

    repetition_estimates: List[CausalEstimate]
    repetition_seeds: List[int]
