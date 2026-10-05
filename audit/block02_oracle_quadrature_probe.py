"""Independent deterministic quadrature accuracy probe for the B02 oracle fix."""

import json

import numpy as np
from scipy.integrate import quad
from scipy.special import expit
from scipy.stats import norm

from causalis.dgp.multicausaldata import MultiCausalDatasetGenerator


def main():
    links = np.linspace(-0.6, 1.6, 23)
    for strength in [0.6, 1.5, 2.0, 2.00001, 3.0, 5.0, 10.0]:
        generator = MultiCausalDatasetGenerator(k=0, u_strength_y=strength)
        actual = generator._marginal_natural_scale_from_link(links, "binary")
        reference = np.asarray(
            [
                quad(
                    lambda z: expit(location + strength * z) * norm.pdf(z),
                    -12.0,
                    12.0,
                    epsabs=1e-13,
                    epsrel=1e-13,
                )[0]
                for location in links
            ]
        )
        print(
            json.dumps(
                {
                    "strength": strength,
                    "max_absolute_error": float(np.max(np.abs(actual - reference))),
                }
            )
        )


if __name__ == "__main__":
    main()
