"""Read-only reference-law review; run via the repository-local Python."""

import json
from pathlib import Path

import numpy as np
from scipy.integrate import quad
from scipy.special import ndtr, softmax
from scipy.stats import norm

from causalis.dgp.multicausaldata import MultiCausalDatasetGenerator
from causalis.dgp.base import _gaussian_copula


def main():
    alpha = np.zeros(3)
    ud = np.array([0.0, 1.0, 1.0])
    uy = 1.0
    theta = np.array([0.0, 0.7, -0.4])
    probability = lambda u: softmax(alpha + ud * u)
    structural_mean = lambda u: np.exp(np.clip(theta + uy * u, -20.0, 20.0))
    integrate = lambda function: quad(
        lambda u: function(u) * norm.pdf(u),
        -12.0,
        12.0,
        epsabs=1e-12,
        epsrel=1e-12,
    )[0]
    marginal = np.array(
        [integrate(lambda u: probability(u)[k]) for k in range(3)]
    )
    outcome_mean = np.array(
        [integrate(lambda u: structural_mean(u)[k]) for k in range(3)]
    )
    true_att = np.array(
        [
            integrate(
                lambda u: (structural_mean(u)[k] - structural_mean(u)[0])
                * probability(u)[k]
            )
            / marginal[k]
            for k in [1, 2]
        ]
    )
    target = np.array([0.2, 0.3, 0.5])
    calibrated = MultiCausalDatasetGenerator(
        k=0, target_d_rate=target, u_strength_d=2.0, seed=731
    ).generate(30000)
    calibrated_alpha = np.log(target) - np.log(target).mean()
    calibrated_ud = np.array([0.0, 2.0, 2.0])
    calibrated_marginal = [
        integrate(lambda u: softmax(calibrated_alpha + calibrated_ud * u)[k])
        for k in range(3)
    ]
    copula_x, _ = _gaussian_copula(
        np.random.default_rng(731),
        200000,
        [
            {"name": "binary_1", "dist": "bernoulli", "p": 0.5},
            {"name": "binary_2", "dist": "bernoulli", "p": 0.5},
        ],
        np.array([[1.0, 0.3], [0.3, 1.0]]),
    )
    both_binary_one = quad(
        lambda z: ndtr(0.3 * z / np.sqrt(1.0 - 0.3**2)) * norm.pdf(z),
        0.0,
        12.0,
        epsabs=1e-12,
        epsrel=1e-12,
    )[0]
    generator = MultiCausalDatasetGenerator(
        k=0,
        n_treatments=3,
        alpha_d=alpha,
        theta=theta,
        outcome_type="gamma",
        u_strength_d=ud,
        u_strength_y=uy,
        seed=731,
    )
    frame = generator.generate(30000)
    assignment_rng = np.random.default_rng(731)
    assignment_rng.normal(size=30000)
    first_uniform_draw = assignment_rng.random(30000)
    first_classes = (
        first_uniform_draw[:, None]
        < frame[["m_obs_d_0", "m_obs_d_1", "m_obs_d_2"]].to_numpy().cumsum(axis=1)
    ).argmax(axis=1)
    result = {
        "seed": 731,
        "n": len(frame),
        "m_zero": frame[["m_d_0", "m_d_1", "m_d_2"]].iloc[0].tolist(),
        "m_marginal_adaptive": marginal.tolist(),
        "empirical_m_obs_mean": frame[
            ["m_obs_d_0", "m_obs_d_1", "m_obs_d_2"]
        ].mean().tolist(),
        "empirical_arm_shares": frame[["d_0", "d_1", "d_2"]].mean().tolist(),
        "first_draw_assignment_matches_frame": bool(
            np.array_equal(first_classes, frame[["d_0", "d_1", "d_2"]].to_numpy().argmax(axis=1))
        ),
        "first_draw_arm_counts": np.bincount(first_classes, minlength=3).tolist(),
        "g_adaptive": outcome_mean.tolist(),
        "g_reported": frame[["g_d_0", "g_d_1", "g_d_2"]].iloc[0].tolist(),
        "marginal_cate": (outcome_mean[1:] - outcome_mean[0]).tolist(),
        "treated_mean_reported_cate": [
            float(frame.loc[frame[f"d_{k}"] == 1, f"cate_d_{k}"].mean())
            for k in [1, 2]
        ],
        "true_population_att_adaptive": true_att.tolist(),
        "calibration": {
            "target": target.tolist(),
            "m_zero_mean": calibrated[["m_d_0", "m_d_1", "m_d_2"]].mean().tolist(),
            "m_marginal_adaptive": calibrated_marginal,
            "empirical_m_obs_mean": calibrated[
                ["m_obs_d_0", "m_obs_d_1", "m_obs_d_2"]
            ].mean().tolist(),
            "empirical_arm_shares": calibrated[["d_0", "d_1", "d_2"]].mean().tolist(),
            "latent_treatment_strength": calibrated_ud.tolist(),
        },
        "copula": {
            "latent_gaussian_correlation": 0.3,
            "population_binary_pearson_correlation_adaptive": 4.0 * both_binary_one - 1.0,
            "observed_binary_pearson_correlation": float(np.corrcoef(copula_x.T)[0, 1]),
            "n": len(copula_x),
            "marginal_bernoulli_probability": 0.5,
        },
        "scope": "reference calculations and reproduction; no runtime changes",
    }
    serialized = json.dumps(result, indent=2)
    Path(__file__).with_name("block07_dgp_probe_result.json").write_text(
        serialized + "\n", encoding="utf-8"
    )
    print(serialized)


if __name__ == "__main__":
    main()
