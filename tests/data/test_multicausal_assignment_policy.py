import numpy as np
import pandas as pd
import pytest

from causalis.dgp.multicausaldata import MultiCausalDatasetGenerator
from causalis.dgp.multicausaldata.functional import generate_multitreatment


def test_public_fallback_preserves_every_existing_arm():
    df = MultiCausalDatasetGenerator(
        k=0, alpha_d=[0.0, 0.0, -1000.0], seed=3
    ).generate(3, U=np.zeros(3))
    assert (df[["d_0", "d_1", "d_2"]].sum() > 0).all()


@pytest.mark.parametrize("seed", range(20))
@pytest.mark.parametrize("n,K", [(3, 3), (5, 5), (8, 5)])
def test_fallback_coverage_for_rare_and_zero_support_arms(seed, n, K):
    probs = np.zeros((n, K))
    probs[:, :2] = [0.8, 0.2]
    result = MultiCausalDatasetGenerator(n_treatments=K, seed=seed)._draw_multinomial(probs)
    assert np.array_equal(np.unique(result), np.arange(K))


@pytest.mark.parametrize("n,K", [(1, 3), (2, 5), (50, 3)])
def test_iid_one_draw_matches_independent_reference_and_rng(n, K):
    probs = np.tile(np.arange(1, K + 1, dtype=float), (n, 1))
    probs /= probs.sum(axis=1, keepdims=True)
    reference = np.random.default_rng(891)
    uniforms = reference.random(n)
    expected = np.array([
        np.searchsorted(np.cumsum(row), u, side="right")
        for row, u in zip(probs, uniforms)
    ])
    gen = MultiCausalDatasetGenerator(n_treatments=K, seed=891, assignment_policy="iid")
    actual = gen._draw_multinomial(probs)
    np.testing.assert_array_equal(actual, expected)
    assert gen.rng.random() == reference.random()


def test_iid_zero_support_and_small_public_sample():
    gen = MultiCausalDatasetGenerator(k=0, alpha_d=[0.0, -1000.0, -1000.0],
                                     seed=9, assignment_policy="iid")
    df = gen.generate(1, U=np.zeros(1))
    np.testing.assert_array_equal(df[["d_0", "d_1", "d_2"]], [[1, 0, 0]])
    assert df[["m_obs_d_1", "m_obs_d_2"]].eq(0).all().all()


def test_ensure_all_small_sample_rejected():
    with pytest.raises(ValueError, match="n must"):
        MultiCausalDatasetGenerator(k=0).generate(2)


@pytest.mark.parametrize("policy", ["unknown", "IID", None, 1])
def test_invalid_policy_rejected_on_initialization(policy):
    with pytest.raises(ValueError, match="assignment_policy"):
        MultiCausalDatasetGenerator(assignment_policy=policy)


def test_mutated_policy_rejected_before_sampler_runs():
    def forbidden(*args):
        raise AssertionError("sampler must not run")
    gen = MultiCausalDatasetGenerator(x_sampler=forbidden)
    gen.assignment_policy = "unknown"
    with pytest.raises(ValueError, match="assignment_policy"):
        gen.generate(10)


def test_wrapper_forwards_policy_and_preserves_default():
    iid = generate_multitreatment(n=1, assignment_policy="iid")
    assert len(iid) == 1
    pd.testing.assert_frame_equal(generate_multitreatment(n=50),
                                 generate_multitreatment(n=50, assignment_policy="ensure_all"))


def test_first_success_default_matches_legacy_public_outcomes_and_rng():
    # Independently consume X, U, assignment uniforms, and outcome noise.
    n = 50
    ref = np.random.default_rng(77)
    X = ref.normal(size=(n, 2))
    ref.normal(size=n)
    uniforms = ref.random(n)
    classes = np.searchsorted(np.array([1 / 3, 2 / 3, 1.0]), uniforms, side="right")
    assert np.array_equal(np.unique(classes), np.arange(3))
    y = (classes != 0).astype(float) + ref.normal(size=n)
    gen = MultiCausalDatasetGenerator(k=2, seed=77)
    df = gen.generate(n)
    np.testing.assert_array_equal(df[["x1", "x2"]], X)
    np.testing.assert_array_equal(df[["d_0", "d_1", "d_2"]], np.eye(3)[classes])
    np.testing.assert_array_equal(df["y"], y)
    assert gen.rng.bit_generator.state == ref.bit_generator.state


def test_valid_legacy_fallback_preserves_labels_and_rng():
    n, K = 5, 3
    probs = np.tile([1.0, 0.0, 0.0], (n, 1))
    ref = np.random.default_rng(819)
    # Ten legacy draws always produce arm 0; any two insertions are safe.
    for _ in range(10):
        ref.random(n)
    idx = ref.choice(n, size=2, replace=False)
    expected = np.zeros(n, dtype=int)
    expected[idx] = [1, 2]
    gen = MultiCausalDatasetGenerator(seed=819)
    np.testing.assert_array_equal(gen._draw_multinomial(probs), expected)
    assert gen.rng.bit_generator.state == ref.bit_generator.state


def test_deterministic_singleton_proposal_uses_a_surplus_donor():
    class ScriptedRNG:
        def __init__(self):
            self.draws = 0

        def random(self, n):
            assert n == 3
            self.draws += 1
            return np.array([0.1, 0.1, 0.5])

        def choice(self, values, size=None, replace=True):
            if size is not None:
                assert values == 3 and size == 1 and replace is False
                return np.array([2])
            np.testing.assert_array_equal(values, [0, 1])
            return 0

    gen = MultiCausalDatasetGenerator()
    gen.rng = ScriptedRNG()
    actual = gen._draw_multinomial(np.full((3, 3), 1 / 3))
    np.testing.assert_array_equal(actual, [2, 0, 1])
    assert gen.rng.draws == 10
