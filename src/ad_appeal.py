"""Manipulation check on the ad creatives.

Before the delivery experiments, a separate sample drawn from the
psychometrically profiled participants was shown the two creatives of a
design side by side and asked which was more appealing, or whether both
appealed equally. The order of presentation was randomized per
participant. The check establishes that the creatives really do
differentiate along the trait, so a delivery difference between them can
be read as a response to framing rather than to an arbitrary pair of
images.
"""

import numpy as np
import pandas as pd
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportions_ztest


def load_appeal_counts(path="data/derived/ad_appeal_counts.csv"):
    """Load the aggregated preference counts per design and audience."""
    return pd.read_csv(path)


def appeal_table(counts):
    """Preference shares per design and audience, as in Table 7."""
    table = counts.copy()
    table["E"] = (table["n_pref_extravert_ad"] / table["n"] * 100).round(2)
    table["I"] = (table["n_pref_introvert_ad"] / table["n"] * 100).round(2)
    table["Equally"] = (table["n_equally_appealing"] / table["n"] * 100).round(2)
    return table[["design", "audience", "n", "E", "I", "Equally"]]


def appeal_tests(counts):
    """Test whether each group preferred the creative matched to its trait.

    A two proportion z test compares the share choosing the trait matched
    creative against the share choosing the mismatched one, among
    respondents who expressed a preference. Holm correction is applied
    within each audience, since that group is tested once per design.
    """
    rows = []
    for _, row in counts.iterrows():
        matched_column = (
            "n_pref_extravert_ad" if row["audience"] == "Extravert" else "n_pref_introvert_ad"
        )
        other_column = (
            "n_pref_introvert_ad" if row["audience"] == "Extravert" else "n_pref_extravert_ad"
        )
        matched = int(row[matched_column])
        other = int(row[other_column])
        decided = matched + other
        z, p = proportions_ztest([matched, other], [decided, decided])
        rows.append(
            {
                "design": row["design"],
                "audience": row["audience"],
                "n_decided": decided,
                "n_matched": matched,
                "n_mismatched": other,
                "Z": round(z, 2),
                "p_raw": p,
            }
        )

    results = pd.DataFrame(rows)
    results["p_holm"] = np.nan
    for audience, block in results.groupby("audience"):
        corrected = multipletests(block["p_raw"], alpha=0.05, method="holm")[1]
        results.loc[block.index, "p_holm"] = corrected
    results["p_raw"] = results["p_raw"].round(4)
    results["p_holm"] = results["p_holm"].round(4)
    return results.sort_values(["audience", "design"]).reset_index(drop=True)
