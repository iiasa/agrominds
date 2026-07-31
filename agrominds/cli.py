from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Literal

import numpy as np
import polars as pl
import rasterio
import tomllib
import xarray as xr
from tqdm import tqdm

from agrominds import crops
from agrominds.climate_io import ClimateBinReader
from agrominds.features import cal_fix_shift, cal_len_to_hd, process_climate_features
from agrominds.pipeline import ClimateBinIterator, compress, read_co2

SUPPORTED_GCMS = [
    "GFDL-ESM4",
    "IPSL-CM6A-LR",
    "MPI-ESM1-2-HR",
    "MRI-ESM2-0",
    "UKESM1-0-LL",
    "GSWP3",
]
SUPPORTED_CROPS = ["mai", "ri1", "ri2", "soy", "swh"]
SUPPORTED_SSP = ["historical", "ssp126", "ssp245", "ssp370", "ssp585", "obsclim"]
CLIMATE_VARS = ["hurs", "pr", "rsds", "sfcwind", "tasmax", "tasmin"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate agrometeorological indicators from daily climate and crop calendar inputs."
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        type=Path,
        help="Path to the TOML configuration file (default: config.toml).",
    )
    parser.add_argument(
        "--gcm",
        choices=SUPPORTED_GCMS,
        required=True,
        type=str,
        help="Climate model name.",
    )
    parser.add_argument(
        "--crop",
        choices=SUPPORTED_CROPS,
        required=True,
        type=str,
        help="Crop key.",
    )
    parser.add_argument(
        "--ssp",
        choices=SUPPORTED_SSP,
        required=True,
        type=str,
        help="Scenario / SSP.",
    )
    return parser.parse_args(argv)


def config_path_value(value: str, config_dir: Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else config_dir / path


def load_config(config_path: Path) -> dict:
    with config_path.open("rb") as config_file:
        return tomllib.load(config_file)


def read_climate_2015(pxmap_chunk: pl.DataFrame, path_climate_2015: Path, path_landmap: Path, gcm: str, r_id: str) -> pl.DataFrame:
    reader = ClimateBinReader(
        data_dir=path_climate_2015,
        landmap_path=path_landmap,
        climate_vars=CLIMATE_VARS,
        file_years=[(2015, 2020, 2192)],
        file_template=f"{gcm.lower()}_{r_id}_w5e5_ssp245_{{var_name}}_global_daily_{{year_from}}_{{year_to}}.bin",
    )
    return next(ClimateBinIterator(pxmap_chunk, reader, 2015, 2015, block_size=1000))


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config_path = args.config.resolve()
    config = load_config(config_path)
    paths_config = config["paths"]
    config_dir = config_path.parent

    def resolve_path(value: str) -> Path:
        return config_path_value(value, config_dir)

    if args.gcm == "UKESM1-0-LL":
        r_id = "r1i1p1f2"
    else:
        r_id = "r1i1p1f1"

    if args.ssp != "obsclim":
        path_climate = resolve_path(paths_config["isimip3b_root"]) / args.ssp / args.gcm
    else:
        path_climate = resolve_path(paths_config["obsclim_root"])

    path_climate_2015 = resolve_path(paths_config["reference_climate_root"]) / args.gcm
    path_landmap = resolve_path(paths_config["landmap"])
    co2_future_template = paths_config["co2_future"]
    path_co2 = Path(
        resolve_path(paths_config["co2_historical"]) if args.ssp in {"historical", "obsclim"} else resolve_path(co2_future_template.format(ssp=args.ssp))
    )
    path_location = resolve_path(paths_config["location_template"].format(crop=args.crop))
    path_out = resolve_path(paths_config["output_dir"]) / f"agrominds_{args.gcm}_{args.ssp}_{args.crop}_rf.parquet"
    path_mask = resolve_path(paths_config["mask"])

    if args.ssp != "obsclim":
        climate_filename_template = (
            f"{args.gcm.lower()}_{r_id}_w5e5_{args.ssp}_{{var_name}}_global_daily_{{year_from}}_{{year_to}}.bin"
        )
    else:
        climate_filename_template = (
            f"{args.gcm.lower()}-w5e5_obsclim_{{var_name}}_global_daily_{{year_from}}_{{year_to}}.bin"
        )

    if args.ssp == "historical":
        year_from = 1971
        year_to = 2014
        binfile_years = [
            (1971, 1980, 3653),
            (1981, 1990, 3652),
            (1991, 2000, 3653),
            (2001, 2010, 3652),
            (2011, 2014, 1461),
        ]
    elif args.ssp == "obsclim":
        year_from = 1971
        year_to = 2019
        binfile_years = [
            (1971, 1980, 3653),
            (1981, 1990, 3652),
            (1991, 2000, 3653),
            (2001, 2010, 3652),
            (2011, 2019, 3287),
        ]
    else:
        year_from = 2015
        year_to = 2100
        binfile_years = [
            (2015, 2020, 2192),
            (2021, 2030, 3652),
            (2031, 2040, 3653),
            (2041, 2050, 3652),
            (2051, 2060, 3653),
            (2061, 2070, 3652),
            (2071, 2080, 3653),
            (2081, 2090, 3652),
            (2091, 2100, 3652),
        ]

    shift = 0
    crop = {
        "mai": crops.maize,
        "ri1": crops.rice,
        "ri2": crops.rice,
        "soy": crops.soy,
        "swh": crops.wheat_summer,
    }[args.crop]
    cal_mode: Literal["nc_pd_hd", "nc_pd", "master_file"] = "master_file"
    cal_start_year = None

    np.random.seed(42)
    random.seed(42)

    print("Processing")

    loc_data = pl.read_csv(
        path_location,
        schema_overrides={
            "YLAT": pl.Float32,
            "XLON": pl.Float32,
            "PLDOY": pl.Int16,
            "HRDOY": pl.Int16,
            "PHU": pl.Float32,
            "ELEV": pl.Int16,
            "PRMT6": pl.Float32,
            "PRMT74": pl.Float32,
        },
    ).rename(
        {
            "YLAT": "lat",
            "XLON": "lon",
            "PLDOY": "pd",
            "HRDOY": "hd",
            "PHU": "phu",
            "ELEV": "elev",
            "PRMT6": "prmt6",
            "PRMT74": "prmt74",
        }
    ).drop("CLIMATEID")

    with rasterio.open(path_mask) as src:
        mask = src.read(1)

    lat = loc_data["lat"].to_numpy()
    lon = loc_data["lon"].to_numpy()

    row = ((90.0 - lat) * 2).astype(np.int32)
    col = ((lon + 180.0) * 2).astype(np.int32)

    loc_data = loc_data.filter(mask[row, col] > 0)

    co2 = read_co2(path_co2, year_from, year_to)

    if cal_mode != "master_file":
        if cal_mode == "nc_pd_hd":
            cal_xr = xr.open_mfdataset(
                [path_pd, path_hd],
                combine="by_coords",
                chunks=None,
                decode_times=False,
            ).rename({"plantday-mai-firr": "pd", "matyday-mai-firr": "hd", "time": "year"})

        elif cal_mode == "nc_pd":
            cal_xr = xr.open_dataset(path_pd, decode_times=False).rename(
                {"plantday-mai-firr": "pd", "time": "year"}
            )
            cal_xr = cal_xr.assign(hd=None)

        else:
            raise ValueError("Invalid calendar mode")

        cal_xr = cal_xr.assign_coords(year=np.arange(cal_start_year, cal_start_year + len(cal_xr.year)))
        cal_xr = cal_xr.sel(year=slice(year_from, year_to))

        cal = pl.DataFrame(
            cal_xr.to_dataframe().dropna().reset_index(),
            schema={"lat": pl.Float16, "lon": pl.Float16, "year": pl.Int16, "pd": pl.Int16, "hd": pl.Int16},
        )
        cal_xr.close()
        del cal_xr

        if shift != 0:
            cal = cal_fix_shift(cal, shift)

        cal = cal_len_to_hd(cal)

    else:
        cal = None

    bin_reader = ClimateBinReader(
        data_dir=path_climate,
        landmap_path=path_landmap,
        climate_vars=CLIMATE_VARS,
        file_years=binfile_years,
        file_template=climate_filename_template,
    )

    pixels = set(bin_reader.land_pixels())
    pixels = sorted(pixels)

    pxmap = pl.DataFrame(
        {
            "pixel": range(len(pixels)),
            "lat": [x[0] for x in pixels],
            "lon": [x[1] for x in pixels],
        }
    )

    loc_data = loc_data.join(pxmap, on=["lat", "lon"])
    pxmap = loc_data[["pixel", "lat", "lon"]]

    px_iterator = ClimateBinIterator(pxmap, bin_reader, year_from, year_to, block_size=1000)
    blocks: list[pl.DataFrame] = []
    for climate in tqdm(px_iterator):
        px_chunk = climate.select("pixel").unique().join(pxmap, on="pixel")
        block = climate.join(loc_data, on="pixel").join(co2, on="year")

        if args.ssp == "historical":
            block_2015 = (
                read_climate_2015(px_chunk, path_climate_2015, path_landmap, args.gcm, r_id)
                .join(loc_data, on="pixel")
                .join(co2, on="year")
            )
            block = pl.concat([block, block_2015], how="vertical").sort(["pixel", "year", "day"])

        if cal is not None:
            block = block.join(
                cal,
                on=["lat", "lon", "year"],
                how="left",
                suffix="_cal",
            ).with_columns(
                [
                    pl.coalesce(["pd_cal", "pd"]).alias("pd"),
                    pl.coalesce(["hd_cal", "hd"]).alias("hd"),
                ]
            ).drop(["pd_cal", "hd_cal"])

        block = block.with_columns(
            pl.col("hurs") / 100,
            pl.col("pr") * 24 * 60 * 60,
            pl.col("rsds") * 60 * 60 * 24 / 1e6,
            pl.col("tasmax") - 273.15,
            pl.col("tasmin") - 273.15,
        ).with_columns(
            tav=(pl.col("tasmax") + pl.col("tasmin")) / 2
        )

        block = process_climate_features(
            block,
            crop=crop,
            calculate_hd="no" if cal_mode == "nc_pd_hd" else "with_fallback",
        )
        blocks.append(block)

    df = pl.concat(blocks, how="vertical").join(pxmap, on="pixel").drop("pixel", "gs")

    if args.ssp == "historical":
        df = df.filter(pl.col("yr") < 2015)

    df = compress(df)
    df.write_parquet(path_out)
    print("done")
