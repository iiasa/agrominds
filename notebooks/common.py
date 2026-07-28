from pathlib import Path
from typing import Literal
import tomllib
import numpy as np
import polars as pl
import rasterio


ssps = ["historical", "ssp126", "ssp245", "ssp370", "ssp585", "obsclim"]
ggcms = ["GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0", "UKESM1-0-LL", "GSWP3"]
crops = ["mai", "ri1", "ri2", "soy", "swh"]

def compress(df: pl.DataFrame, decompress: bool = False) -> pl.DataFrame:
    ex = []
    for col, f, ctype in [
        ("tmx_av", 100, pl.Int16),
        ("tmn_av", 100, pl.Int16),
        ("tav_av", 100, pl.Int16),
        ("prcp_sum", 1, pl.UInt16),
        ("swr_sum", 1, pl.UInt16),
        ("ws_av", 100, pl.UInt16),
        ("rh_av", 1000, pl.UInt16),
        ("pet_sum", 10, pl.UInt16),
        ("gdd_sum", 1, pl.UInt16),
        ("cmd_sum", 1, pl.Int16),
        ("len", 1, pl.UInt16),
        ("hui", 1000, pl.UInt16),
        ("yr", 1, pl.UInt16),
        ("lat", 100, pl.Int16),
        ("lon", 100, pl.Int16),
        ("hdd", 1, pl.UInt16),
        ("kdd", 1, pl.UInt16),
        ("frt", 1, pl.UInt16),
        ("ice", 1, pl.UInt16),
        ("r10", 1, pl.UInt16),
        ("r20", 1, pl.UInt16),
        ("wet", 1, pl.UInt16),
        ("dry", 1, pl.UInt16),
        ("mdd", 1, pl.UInt16),
        ("cwd", 1, pl.UInt16),
        ("cdd", 1, pl.UInt16),
    ]:
        if not decompress:
            if col == "pet_sum":
                expr = pl.col(col).clip(lower_bound=0)
            else:
                expr = pl.col(col)
            ex.append((expr * f).round().cast(ctype))              
            # ex.append((pl.col(col) * f).round().cast(ctype))
        else:
            t = ctype if f == 1 else pl.Float32
            ex.append((pl.col(col) * (1 / f)).cast(t))

    return df.with_columns(ex)

def load_data(ssp, gcm, crop) -> pl.DataFrame:
    config_path = Path(__file__).resolve().parent.parent / "config.toml"
    with config_path.open("rb") as config_file:
        paths_config = tomllib.load(config_file)["paths"]

    output_dir = Path(paths_config["output_dir"]).expanduser()
    if not output_dir.is_absolute():
        output_dir = config_path.parent / output_dir

    output_name = paths_config["output_filename_template"].format(
        ssp=ssp,
        gcm=gcm,
        crop=crop,
    )
    return compress(pl.read_parquet(output_dir / output_name), True)

def load_spam_w(path_mask: Path) -> pl.DataFrame:
    with rasterio.open(path_mask) as src:
        area = src.read(1)
        transform = src.transform
        nodata = src.nodata
    
    # Keep valid, positive cells
    valid = area > 0
    
    if nodata is not None:
        valid &= area != nodata
    
    rows, cols = np.where(valid)
    
    # Cell-center coordinates
    lon, lat = rasterio.transform.xy(
        transform,
        rows,
        cols,
        offset="center",
    )
    
    spam_area = pl.DataFrame({
        "lat": np.asarray(lat),
        "lon": np.asarray(lon),
        "W": area[rows, cols],
    })

    # Convert 10x10km to halfdegree
    spam_halfdeg = (
        spam_area
        .with_columns(
            ((pl.col("lat") * 2).floor() / 2 + 0.25).alias("lat_05"),
            ((pl.col("lon") * 2).floor() / 2 + 0.25).alias("lon_05"),
        )
        .group_by(["lat_05", "lon_05"])
        .agg(
            pl.col("W").sum().alias("W")
        )
        .rename({
            "lat_05": "lat",
            "lon_05": "lon",
        })
    )

    return spam_halfdeg
