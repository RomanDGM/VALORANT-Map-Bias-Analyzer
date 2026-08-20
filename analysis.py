# analysis.py — Statistical analysis of map-side bias in VALORANT

import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from scipy.stats import chi2_contingency
import statsmodels.api as sm
import warnings
warnings.filterwarnings("ignore")

from database import get_team_results


def load_dataframe():
    """Load team results from the DB into a DataFrame."""
    rows = get_team_results()
    if not rows:
        raise ValueError("[Analysis] No data in the database. Run the scraper first.")

    df = pd.DataFrame(rows, columns=["map_name", "starting_side", "won"])
    df["won"] = df["won"].astype(int)
    return df


def compute_win_rates(df):
    """Compute win rate per map and starting side."""
    stats = (
        df.groupby(["map_name", "starting_side"])["won"]
        .agg(["sum", "count"])
        .rename(columns={"sum": "wins", "count": "total"})
        .reset_index()
    )
    stats["win_rate"] = stats["wins"] / stats["total"]
    return stats


def classify_maps(stats):
    """
    Classify each map as 'ATTACKER', 'DEFENDER', or 'BALANCED'
    based on the win-rate differential between sides.

    Thresholds:
        diff > +0.05  → ATTACKER-sided
        diff < -0.05  → DEFENDER-sided
        otherwise     → BALANCED
    """
    results = []
    for map_name in stats["map_name"].unique():
        map_data = stats[stats["map_name"] == map_name]
        att  = map_data[map_data["starting_side"] == "attacker"]["win_rate"].values
        deff = map_data[map_data["starting_side"] == "defender"]["win_rate"].values

        att_wr  = att[0]  if len(att)  > 0 else 0.5
        def_wr  = deff[0] if len(deff) > 0 else 0.5
        diff    = att_wr - def_wr

        if diff > 0.05:
            classification = "ATTACKER"
        elif diff < -0.05:
            classification = "DEFENDER"
        else:
            classification = "BALANCED"

        results.append({
            "map_name":          map_name,
            "attacker_win_rate": round(att_wr, 4),
            "defender_win_rate": round(def_wr, 4),
            "difference":        round(diff,   4),
            "classification":    classification,
        })

    return pd.DataFrame(results).sort_values("difference", ascending=False)


def run_logistic_regression(df):
    """
    Logistic regression: predicts match outcome (win/loss)
    from map and starting side.

    Note: accuracy near 50% is expected — VALORANT is designed to be
    balanced. The meaningful signal lies in the coefficients and
    per-map statistical tests, not in predictive accuracy.
    """
    print("\n[Analysis] Training logistic regression model...\n")

    le_map  = LabelEncoder()
    le_side = LabelEncoder()

    df = df.copy()
    df["map_encoded"]  = le_map.fit_transform(df["map_name"])
    df["side_encoded"] = le_side.fit_transform(df["starting_side"])

    X = df[["map_encoded", "side_encoded"]]
    y = df["won"]

    if len(y.unique()) < 2:
        print("[Analysis] Not enough outcome variety to train.")
        return None, None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = LogisticRegression(max_iter=500)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    print("=== CLASSIFICATION REPORT ===")
    print(classification_report(y_test, y_pred, target_names=["Loss", "Win"]))

    print("=== CONFUSION MATRIX ===")
    print(confusion_matrix(y_test, y_pred))
    print()

    # AUC-ROC — more informative than accuracy for near-random binary classification
    y_prob = model.predict_proba(X_test)[:, 1]
    auc    = roc_auc_score(y_test, y_prob)
    print("=== AUC-ROC ===")
    print(f"  {auc:.4f}  (0.5 = random, 1.0 = perfect)")
    if auc > 0.5:
        print("  The model ranks outcomes slightly better than random chance.")
    else:
        print("  The model does not outperform random chance.")
    print()

    # Model coefficients
    coef_df = pd.DataFrame({
        "Feature":     ["map_encoded", "side_encoded"],
        "Coefficient": model.coef_[0],
    })
    print("=== MODEL COEFFICIENTS ===")
    print(coef_df.to_string(index=False))
    print()

    return model, (le_map, le_side)


def run_chi_square(df):
    """
    Chi-square test of independence per map.

    Question: is starting side (attacker/defender) significantly associated
    with winning? p < 0.05 means the association is unlikely to be random.
    """
    print("=== CHI-SQUARE TEST PER MAP (does side matter?) ===")
    print(f"{'Map':<12} {'p-value':>10}  {'Significant':>13}  {'Interpretation'}")
    print("-" * 65)

    results = []
    for map_name in sorted(df["map_name"].unique()):
        sub   = df[df["map_name"] == map_name]
        table = pd.crosstab(sub["starting_side"], sub["won"])
        if table.shape != (2, 2):
            continue

        chi2, p, dof, expected = chi2_contingency(table)
        sig    = "✓ YES" if p < 0.05 else "✗ NO"
        interp = "side affects outcome" if p < 0.05 else "could be chance"
        print(f"{map_name:<12} {p:>10.4f}  {sig:>13}  {interp}")
        results.append({"map_name": map_name, "p_value": p, "significant": p < 0.05})

    print()
    return pd.DataFrame(results)


def run_odds_ratio(df):
    """
    Logistic regression (statsmodels) per map.

    Reports the Odds Ratio + 95% CI for the attacker side.
    OR > 1 → attacking increases win probability.
    OR < 1 → defending increases win probability.
    """
    print("=== ODDS RATIO PER MAP (effect of attacking side) ===")
    print(f"{'Map':<12} {'OR':>6}  {'95% CI':>18}  {'p-value':>8}  {'Conclusion'}")
    print("-" * 75)

    results = []
    for map_name in sorted(df["map_name"].unique()):
        sub = df[df["map_name"] == map_name].copy()
        sub["is_attacker"] = (sub["starting_side"] == "attacker").astype(int)

        X = sm.add_constant(sub["is_attacker"])
        y = sub["won"]

        try:
            logit_model = sm.Logit(y, X).fit(disp=0)
            or_val      = np.exp(logit_model.params["is_attacker"])
            ci          = np.exp(logit_model.conf_int().loc["is_attacker"])
            p_val       = logit_model.pvalues["is_attacker"]

            if p_val < 0.05:
                conclusion = "Attacking HELPS" if or_val > 1 else "Defending HELPS"
            else:
                conclusion = "No significant effect"

            print(f"{map_name:<12} {or_val:>6.3f}  [{ci[0]:.3f} – {ci[1]:.3f}]  {p_val:>8.4f}  {conclusion}")
            results.append({
                "map_name":    map_name,
                "odds_ratio":  or_val,
                "ci_low":      ci[0],
                "ci_high":     ci[1],
                "p_value":     p_val,
                "significant": p_val < 0.05,
            })
        except Exception as e:
            print(f"{map_name:<12} Error: {e}")

    print()
    return pd.DataFrame(results)


def predict(model, encoders, map_name, side):
    """Predict win probability for a given map and starting side."""
    le_map, le_side = encoders

    try:
        map_enc  = le_map.transform([map_name])[0]
        side_enc = le_side.transform([side])[0]
    except ValueError as e:
        print(f"[Predict] Error: {e}")
        return None

    prob = model.predict_proba([[map_enc, side_enc]])[0]
    print(f"\n[Predict] Map: {map_name} | Side: {side}")
    print(f"  → Win probability:  {prob[1]:.2%}")
    print(f"  → Loss probability: {prob[0]:.2%}")
    return prob


def run_full_analysis():
    """Run the complete analysis pipeline and return all results."""
    df = load_dataframe()
    print(f"[Analysis] {len(df)} records loaded.\n")

    stats          = compute_win_rates(df)
    classification = classify_maps(stats)

    print("=== MAP CLASSIFICATION ===")
    print(classification.to_string(index=False))
    print()

    model, encoders = run_logistic_regression(df)
    chi_results     = run_chi_square(df)
    or_results      = run_odds_ratio(df)

    return {
        "dataframe":      df,
        "win_rates":      stats,
        "classification": classification,
        "model":          model,
        "encoders":       encoders,
        "chi_square":     chi_results,
        "odds_ratios":    or_results,
    }
