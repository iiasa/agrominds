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
        ("TMXav", 100, pl.Int16),
        ("TMNav", 100, pl.Int16),
        ("TAVav", 100, pl.Int16),
        ("PRCPsum", 1, pl.UInt16),
        ("RADsum", 1, pl.UInt16),
        ("WSDav", 100, pl.UInt16),
        ("HURav", 1000, pl.UInt16),
        ("PETsum", 10, pl.UInt16),
        ("GDDsum", 1, pl.UInt16),
        ("CMDsum", 1, pl.Int16),
        ("LEN", 1, pl.UInt16),
        ("HUIeop", 1000, pl.UInt16),
        ("YR", 1, pl.UInt16),
        ("LAT", 100, pl.Int16),
        ("LON", 100, pl.Int16),
        ("HDD", 1, pl.UInt16),
        ("KDD", 1, pl.UInt16),
        ("FRT", 1, pl.UInt16),
        ("ICE", 1, pl.UInt16),
        ("R10", 1, pl.UInt16),
        ("R20", 1, pl.UInt16),
        ("WET", 1, pl.UInt16),
        ("DRY", 1, pl.UInt16),
        ("CMDgt0", 1, pl.UInt16),
        ("CWD", 1, pl.UInt16),
        ("CDD", 1, pl.UInt16),
    ]:
        if not decompress:
            if col == "PETsum":
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
        "LAT": np.asarray(lat),
        "LON": np.asarray(lon),
        "W": area[rows, cols],
    })

    # Convert 10x10km to halfdegree
    spam_halfdeg = (
        spam_area
        .with_columns(
            ((pl.col("LAT") * 2).floor() / 2 + 0.25).alias("LAT_05"),
            ((pl.col("LON") * 2).floor() / 2 + 0.25).alias("LON_05"),
        )
        .group_by(["LAT_05", "LON_05"])
        .agg(
            pl.col("W").sum().alias("W")
        )
        .rename({
            "LAT_05": "LAT",
            "LON_05": "LON",
        })
    )

    return spam_halfdeg
