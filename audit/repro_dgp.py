"""DGP audit: user ID collisions and nonlinear latent oracle scale."""
import json
from pathlib import Path

import numpy as np

from causalis.dgp.causaldata.functional import generate_rct
from causalis.dgp.multicausaldata.base import MultiCausalDatasetGenerator


def main():
    raw = generate_rct(n=20_000, random_state=42, add_pre=False, return_causal_data=False)
    duplicates = int(raw.user_id.duplicated().sum())
    try:
        generate_rct(n=20_000, random_state=42, add_pre=False, return_causal_data=True)
        contract_result = "accepted"
    except Exception as exc:
        contract_result = str(exc)
    gen = MultiCausalDatasetGenerator(n_treatments=3, k=1, theta=[0, 1, 2],
                                      beta_y=[0], alpha_y=0, outcome_type="gamma",
                                      u_strength_y=1, u_strength_d=0, seed=23, include_oracle=True)
    sample = gen.generate(200_000)
    results = {"uuid_20_bits": {"n": len(raw), "duplicate_ids_in_raw": duplicates,
                                "contract_result": contract_result,
                                "expected_collision_pairs": 20_000*19_999/(2*16**5)},
               "multi_gamma_latent_oracle": {"oracle_control": float(sample.g_d_0.mean()),
                                               "true_control_mean_unclipped": float(np.exp(.5)),
                                               "empirical_control_mean": float(sample.loc[sample.d_0 == 1, "y"].mean()),
                                               "oracle_cate_1": float(sample.cate_d_1.mean()),
                                               "true_cate_1_unclipped": float(np.exp(.5)*(np.exp(1)-1))}}
    (Path(__file__).parent / "results_dgp.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
