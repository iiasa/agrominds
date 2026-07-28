from pathlib import Path

import polars as pl

from agrominds import crops
from agrominds.features import process_climate_features
from agrominds.pipeline import compress


FIXTURE_DIR = Path(__file__).parent / "data"

FINAL_COLUMNS = {
    "tmx_av", "tmn_av", "tav_av", "prcp_sum", "swr_sum", "ws_av",
    "rh_av", "pet_sum", "gdd_sum", "cmd_sum", "len", "hui", "hdd",
    "kdd", "frt", "ice", "r10", "r20", "wet", "dry", "mdd", "cwd",
    "cdd", "yr", "lat", "lon", "period",
}


def test_minimal_location_fixture_runs_feature_pipeline():
    """A small master-location fixture produces the public final schema."""
    location = (
        pl.read_csv(FIXTURE_DIR / "location_mai_minimal.csv")
        .rename({
            "CLIMATEID": "pixel",
            "YLAT": "lat",
            "XLON": "lon",
            "PLDOY": "pd",
            "HRDOY": "hd",
            "PHU": "phu",
            "ELEV": "elev",
            "PRMT6": "prmt6",
            "PRMT74": "prmt74",
        })
    )

    daily_climate = pl.DataFrame({
        "pixel": [288348] * 35,
        "day": list(range(1, 36)),
        "year": [2000] * 35,
        "tasmax": [25.0] * 35,
        "tasmin": [15.0] * 35,
        "tav": [20.0] * 35,
        "pr": [2.0] * 35,
        "rsds": [15.0] * 35,
        "sfcwind": [2.0] * 35,
        "hurs": [0.6] * 35,
        "co2": [370.0] * 35,
    })

    result = process_climate_features(
        daily_climate.join(location, on="pixel"), crop=crops.maize
    )
    final = (
        result
        .join(location.select("pixel", "lat", "lon"), on="pixel")
        .drop("pixel", "gs")
    )

    assert FINAL_COLUMNS <= set(final.columns)
    assert {"gs", "gs_p"} <= set(final["period"].cast(pl.String).unique())
    assert set(compress(final).columns) == set(final.columns)
