"""Pure comparison-population rule shared by DID support and estimation."""

from __future__ import annotations

from typing import Hashable, Mapping, Sequence


def _comparison_unit_ids(
    unit_ids: Sequence[Hashable],
    first_treatment_by_unit: Mapping[Hashable, Hashable | None],
    time_index: Mapping[Hashable, int | float],
    *,
    cohort: Hashable,
    base_time: Hashable,
    target_time: Hashable,
    control_group: str,
    anticipation: int,
) -> tuple[Hashable, ...]:
    """Select controls in input order for an already validated two-period cell.

    A not-yet-treated control must be outside the evaluated cohort and remain
    untreated, including the anticipation window, at *both* outcome dates.
    With a universal pre-treatment base the base can be later than the target,
    so the eligibility threshold uses the later date. Missing observations are
    handled separately by the caller's complete-pair rule.
    """
    cutoff = max(time_index[base_time], time_index[target_time]) + anticipation
    out = []
    for unit in unit_ids:
        first = first_treatment_by_unit[unit]
        if first == cohort:
            continue
        if first is None:
            include = control_group != "not_yet_treated"
        else:
            include = control_group != "never_treated" and time_index[first] > cutoff
        if include:
            out.append(unit)
    return tuple(out)
