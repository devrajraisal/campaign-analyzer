import pandas as pd
import pytest

from campaign_analyzer.sample_data import generate_sample


def test_same_seed_gives_identical_data():
    pd.testing.assert_frame_equal(generate_sample(10, seed=1), generate_sample(10, seed=1))


def test_different_seeds_give_different_data():
    assert not generate_sample(10, seed=1).equals(generate_sample(10, seed=2))


def test_shape_and_ranges():
    data = generate_sample(days=7)
    assert len(data) == 7 * 5 * 2
    assert (data[["impressions", "clicks", "spend", "conversions", "revenue"]] >= 0).all().all()
    assert (data["clicks"] <= data["impressions"]).all()
    assert (data["conversions"] <= data["clicks"]).all()


def test_rejects_zero_days():
    with pytest.raises(ValueError):
        generate_sample(days=0)
