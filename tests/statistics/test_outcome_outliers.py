import pandas as pd
import pytest

from causalis.dgp.causaldata import CausalData
from causalis.dgp.multicausaldata import MultiCausalData
from causalis.shared import outcome_outliers


def _make_data():
    df = pd.DataFrame({
        "treatment": [0] * 6 + [1] * 6,
        "outcome": [1, 1, 1, 1, 1, 100, 2, 2, 2, 2, 2, 2],
        "confounder": list(range(12)),
    })
    return CausalData.from_df(
        df,
        treatment="treatment",
        outcome="outcome",
        confounders=["confounder"],
    )


def test_outcome_outliers_iqr():
    data = _make_data()

    summary = outcome_outliers(data)
    row0 = summary.loc[summary["treatment"] == 0].iloc[0]
    row1 = summary.loc[summary["treatment"] == 1].iloc[0]

    assert row0["outlier_count"] == 1
    assert bool(row0["has_outliers"]) is True
    assert row1["outlier_count"] == 0
    assert bool(row1["has_outliers"]) is False
    assert row0["outlier_rate"] == pytest.approx(1 / 6)


def test_outcome_outliers_return_rows():
    data = _make_data()

    summary, outliers = outcome_outliers(data, return_rows=True)

    assert summary.shape[0] == 2
    assert outliers.shape[0] == 1
    assert outliers["outcome"].iloc[0] == 100
    assert list(outliers.columns) == ["outcome", "treatment", "confounder"]


def _make_multicausal_data():
    n = 6
    df = pd.DataFrame(
        {
            "y": [1, 1, 1, 1, 1, 100] + [2] * n + [3] * n,
            "t0": [1] * n + [0] * n + [0] * n,
            "t1": [0] * n + [1] * n + [0] * n,
            "t2": [0] * n + [0] * n + [1] * n,
            "x": list(range(3 * n)),
        }
    )
    return MultiCausalData(
        df=df,
        outcome="y",
        treatment_names=["t0", "t1", "t2"],
        confounders=["x"],
        control_treatment="t0",
    )


def test_outcome_outliers_multicausal_default_treatment():
    data = _make_multicausal_data()

    summary, outliers = outcome_outliers(data, return_rows=True)
    row_t0 = summary.loc[summary["treatment"] == "t0"].iloc[0]
    row_t1 = summary.loc[summary["treatment"] == "t1"].iloc[0]
    row_t2 = summary.loc[summary["treatment"] == "t2"].iloc[0]

    assert row_t0["outlier_count"] == 1
    assert bool(row_t0["has_outliers"]) is True
    assert row_t1["outlier_count"] == 0
    assert row_t2["outlier_count"] == 0
    assert outliers.shape[0] == 1
    assert outliers["y"].iloc[0] == 100
    assert outliers["t0"].iloc[0] == 1


@pytest.mark.parametrize("multi", [False, True], ids=["binary", "multi"])
@pytest.mark.parametrize("method", ["iqr", "zscore"])
def test_outlier_rows_use_positions_when_index_labels_are_duplicated(multi, method):
    # Four outliers share one label with each other and with ordinary rows in
    # both arms. Label lookup would include ordinary rows and duplicate results.
    frame = pd.DataFrame({
        "y": [1] * 8 + [100, 110] + [2] * 8 + [200, 220],
        "t0": [1] * 10 + [0] * 10,
        "t1": [0] * 10 + [1] * 10,
        "x": list(range(20)),
    }, index=pd.Index(["shared"] * 20, name="sample"))
    if multi:
        data = MultiCausalData(
            df=frame, outcome="y", treatment_names=["t0", "t1"],
            confounders=["x"], control_treatment="t0",
        )
    else:
        data = CausalData.from_df(frame, outcome="y", treatment="t1", confounders=["x"])
    snapshot = data.df.copy(deep=True)

    summary, outliers = outcome_outliers(data, method=method, z_thresh=1.5, return_rows=True)

    assert summary.outlier_count.tolist() == [2, 2]
    assert len(outliers) == summary.outlier_count.sum() == 4
    pd.testing.assert_frame_equal(outliers, snapshot.iloc[[8, 9, 18, 19]])
    pd.testing.assert_frame_equal(data.df, snapshot)
