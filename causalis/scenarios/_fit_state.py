"""Publish complete fits and detach returned diagnostic payloads."""
from copy import copy, deepcopy
from functools import wraps


_INFERENCE_ATTRIBUTES = (
    'coef_', 'se_', 't_stat_', 'pval_', 'confint_', 'summary_',
    'psi_', 'psi_a_', 'psi_b_', 'mu_c_', 'se_relative_',
    'confint_relative_', 'normalize_ipw_effective_',
)


def _publish_complete_fit(function):
    """Keep the previous fit if fitting a replacement raises.

    Fit methods replace arrays rather than modifying an existing fit in place.
    The staging copy shares supplied learner/configuration objects: this is
    model-state publication, not rollback of user callbacks or external state.
    """
    @wraps(function)
    def fit(self, *args, **kwargs):
        candidate = copy(self)
        function(candidate, *args, **kwargs)
        for name in _INFERENCE_ATTRIBUTES:
            candidate.__dict__.pop(name, None)
        self.__dict__.clear()
        self.__dict__.update(candidate.__dict__)
        return self
    return fit


def _diagnostic_snapshot(diagnostic):
    """Copy payload fields while retaining any private live-model reference.

    A returned payload owns its arrays and nested caches. The private model
    link used by refutation adapters deliberately retains its existing meaning.
    """
    if diagnostic is None:
        return None
    return diagnostic.model_copy(update={
        name: deepcopy(getattr(diagnostic, name))
        for name in type(diagnostic).model_fields
    })
