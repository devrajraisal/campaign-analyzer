import io

import pytest

from campaign_analyzer.loader import load_campaigns
from campaign_analyzer.sample_data import generate_sample


@pytest.fixture(scope="session")
def sample_df():
    """The synthetic sample, loaded the same way a real file would be."""
    csv = generate_sample(days=60, seed=42).to_csv(index=False)
    return load_campaigns(io.StringIO(csv)).data


def csv_text(rows, header="date,campaign,impressions,clicks,spend"):
    return io.StringIO("\n".join([header, *rows]) + "\n")
