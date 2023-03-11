# Copyright 2022 OpenMined.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Exact and approximate computations for Poisson binomial distribution.

More details on Poisson binomial distribution https://en.wikipedia.org/wiki/Poisson_binomial_distribution
"""

import numpy as np
from scipy.stats import norm
from typing import Sequence, Tuple
from dataclasses import dataclass


@dataclass
class PMF:
    """Represents probability mass function of a finite integer value distribution.

    Attributes:
        start: the minimal value that this distribution can produce.
        probabilities: the i-th element represents the probability that the
         distribution attains value i+start.

    """
    start: int
    probabilities: np.ndarray


def compute_pmf(probabilities: Sequence[float]) -> np.ndarray:
    """Computes probability mass function of Poisson binomial distribution."""
    # Compute coefficients of Probability Generating Function (PGF), which
    # equals to
    # PGF(x) = \product_{p\in ps}(1-p + p*x)
    poisson_bin_probs = np.array([1])
    for p in probabilities:
        next_poisson_bin_probs = np.zeros(len(poisson_bin_probs) + 1)
        next_poisson_bin_probs[:-1] = poisson_bin_probs * (1 - p)
        next_poisson_bin_probs[1:] += poisson_bin_probs * p
        poisson_bin_probs = next_poisson_bin_probs
    return PMF(0, poisson_bin_probs)


def compute_exp_std_skewness(
        probabilities: Sequence[float]) -> Tuple[float, float, float]:
    exp = np.sum(probabilities)
    std = np.sqrt(np.sum([p * (1 - p) for p in probabilities]))
    skewness = np.sum([p * (1 - p) * (1 - 2 * p) for p in probabilities
                      ]) / std**3
    return exp, std, skewness


def compute_pmf_approximation(mean: float, sigma: float, skewness: float,
                              n: int):
    """Computes approximate probability mass function of Poisson binomial distribution.

    The computation is based on paper chapter 3.3 (refined normal approximation)
    https://www.researchgate.net/publication/257017356_On_computing_the_distribution_function_for_the_Poisson_binomial_distribution

    The tails of probability <10^(-15) are dropped.
    """
    if sigma == 0:
        return PMF(int(round(mean)), np.array([1]))
    G = lambda x: (norm.cdf(x) + skewness * (1 - x * x) * norm.pdf(x) / 6)
    # n can be large. Assuming that the output distribution is close to the
    # normal, for all i further than 8*sigma contributes less than 10^(-15).
    # So compute probabilities for (mean-8*sigma, mean+8*sigma).
    start = max(0, int(np.floor(mean - 8 * sigma)))
    end = min(n, int(np.round(mean + 8 * sigma)))

    xs = np.arange(start - 1, end + 1)
    cdf_values = G((xs + 0.5 - mean) / sigma)
    cdf_values = np.clip(cdf_values, 0, 1)
    return PMF(start, np.diff(cdf_values))
