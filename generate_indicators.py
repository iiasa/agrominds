from typing import Literal
import numpy as np
import polars as pl

import xarray as xr
from agrominds.features import cal_fix_shift, cal_len_to_hd, process_climate_features
from agrominds.climate_io import ClimateBinReader
from tqdm import tqdm
import random
from agrominds.pipeline import ClimateBinIterator, read_co2, compress
from agrominds import crops
from pathlib import Path
import rasterio
import argparse
import tomllib


# Args
parser = argparse.ArgumentParser()
parser.add_argument(
    "--config",
    default="config.toml",
    type=Path,
    help="Path to the TOML configuration file (default: config.toml).",
)
parser.add_argument(
    "--gcm", 
    default="GFDL-ESM4",
    choices=["GFDL-ESM4", "IPSL-CM6A-LR", "MPI-ESM1-2-HR", "MRI-ESM2-0", "UKESM1-0-LL", "GSWP3"], 
    required=True,
    type=str
)
parser.add_argument(
    "--crop", 
    default="mai",
    choices=["mai", "ri1", "ri2", "soy", "swh"], 
    required=True,
    type=str
)
parser.add_argument(
    "--ssp", 
    default="historical",
    choices=["historical", "ssp126", "ssp245", "ssp370", "ssp585", "obsclim"], 
    required=True,
    type=str
)

args = parser.parse_args()
config_path = args.config.resolve()
with config_path.open("rb") as config_file:
    config = tomllib.load(config_file)

paths_config = config["paths"]
config_dir = config_path.parent

def config_path_value(value: str) -> Path:
    """Resolve relative paths against the directory containing config.toml."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else config_dir / path

gcm = args.gcm
crop_arg = args.crop
ssp = args.ssp

# Paths
path_pd = None
path_hd = None

if ssp != "obsclim":
    path_climate = config_path_value(paths_config["isimip3b_root"]) / ssp / gcm
else:
    path_climate = config_path_value(paths_config["obsclim_root"])
    
path_climate_2015 = config_path_value(paths_config["reference_climate_root"]) / gcm
path_landmap = config_path_value(paths_config["landmap"])
path_co2 = Path(
    config_path_value(paths_config["co2_historical"])
    if ssp in {"historical", "obsclim"} else
    config_path_value(paths_config["co2_future"])
)
path_location = config_path_value(
    paths_config["location_template"].format(crop=crop_arg)
)
path_out = config_path_value(paths_config["output_dir"]) / paths_config[
    "output_filename_template"
].format(ssp=ssp, gcm=gcm, crop=crop_arg)
path_mask = config_path_value(paths_config["mask"])

if gcm == "UKESM1-0-LL":
    r_id = "r1i1p1f2"
else:
    r_id = "r1i1p1f1"

if ssp != "obsclim":
    climate_filename_template = gcm.lower() + "_" + r_id + "_w5e5_" + ssp + "_{var_name}_global_daily_{year_from}_{year_to}.bin"
else:
    climate_filename_template = gcm.lower() + "-w5e5_obsclim_{var_name}_global_daily_{year_from}_{year_to}.bin"

# Parameters
if ssp == "historical":
    year_from = 1971
    year_to = 2014
    binfile_years = [
        (1971, 1980, 3653), 
        (1981, 1990, 3652),
        (1991, 2000, 3653), 
        (2001, 2010, 3652), 
        (2011, 2014, 1461)
    ]
elif ssp == "obsclim":
    year_from = 1971
    year_to = 2019
    binfile_years = [
        (1971, 1980, 3653), 
        (1981, 1990, 3652),
        (1991, 2000, 3653), 
        (2001, 2010, 3652),
        (2011, 2019, 3287)
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
    "swh": crops.wheat_summer
}[crop_arg]
cal_mode: Literal["nc_pd_hd", "nc_pd", "master_file"] = "master_file"
cal_start_year = None

climate_vars = [
    'hurs',  # Near-Surface Relative Humidity
    'pr',  # Precipitation
    'rsds',  # Surface Downwelling Shortwave Radiation
    'sfcwind',  # Near-Surface Wind Speed
    'tasmax',  # Daily Maximum Near-Surface Air Temperature
    'tasmin',  # Daily Minimum Near-Surface Air Temperature
]

def read_climate_2015(pxmap_chunk):
    ref_ssp = "ssp245"
    reader = ClimateBinReader(
        data_dir=path_climate_2015,
        landmap_path=path_landmap,
        climate_vars=climate_vars,
        file_years=[(2015, 2020, 2192)],
        file_template=gcm.lower() + "_" + r_id + "_w5e5_" + ref_ssp + "_{var_name}_global_daily_{year_from}_{year_to}.bin",
    )
    return next(ClimateBinIterator(pxmap_chunk, reader, 2015, 2015, block_size=1000))

np.random.seed(42)
random.seed(42)

print(f'Processing')

# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *
# Prepare location/master df
# (This df determines the pixel over which the pipeline is applied)
# * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

# In this case, loc_data is already masked by the land pixels.
loc_data = pl.read_csv(
    path_location, 
    schema_overrides = {
        "YLAT": pl.Float32, 
        "XLON": pl.Float32, 
        "PLDOY": pl.Int16, 
        "HRDOY": pl.Int16, 
        "PHU": pl.Float32, 
        "ELEV": pl.Int16, 
        "PRMT6": pl.Float32,
        "PRMT74": pl.Float32,
    }).rename({
        "YLAT": "lat",
        "XLON": "lon",
        "PLDOY": "pd",
        "HRDOY": "hd",
        "PHU": "phu",
        "ELEV": "elev",
        "PRMT6": "prmt6",
        "PRMT74": "prmt74",
    }).drop(
        "CLIMATEID"
    )

# Apply landmask
with rasterio.open(path_mask) as src:
    mask = src.read(1)
    
lat = loc_data["lat"].to_numpy()
lon = loc_data["lon"].to_numpy()

row = ((90.0 - lat) * 2).astype(np.int32)
col = ((lon + 180.0) * 2).astype(np.int32)

loc_data = loc_data.filter(mask[row, col] > 0)

# * * * * * * * * * * * * * * * * * * * * * * * *
# Prepare CO2 data
# * * * * * * * * * * * * * * * * * * * * * * * *

co2 = read_co2(path_co2, year_from, year_to)

# * * * * * * * * * * * * * * * * * * * * * * * *
# Prepare calendar
# * * * * * * * * * * * * * * * * * * * * * * * *

# Open PD (and HD) NCs and convert to polars df
if cal_mode != "master_file":

    if cal_mode == "nc_pd_hd":

        cal_xr = xr.open_mfdataset(
            [path_pd, path_hd], 
            combine="by_coords",
            chunks=None, 
            decode_times=False
        ).rename({"plantday-mai-firr": "pd", "matyday-mai-firr": "hd", "time": "year"})

    elif cal_mode == "nc_pd":
        cal_xr = xr.open_dataset(
            path_pd, 
            decode_times=False
        ).rename({"plantday-mai-firr": "pd", "time": "year"})
        cal_xr = cal_xr.assign(hd=None)
    
    else:
        raise ValueError("Invalid calendar mode")

    cal_xr = cal_xr.assign_coords(year=np.arange(cal_start_year, cal_start_year + len(cal_xr.year)))
    cal_xr = cal_xr.sel(year=slice(year_from, year_to))

    cal = pl.DataFrame(
        cal_xr.to_dataframe().dropna().reset_index(),
        schema={"lat": pl.Float16, "lon": pl.Float16, "year": pl.Int16, "pd": pl.Int16, "hd": pl.Int16}
    )
    cal_xr.close()
    del cal_xr

    # Fix shift
    if shift != 0:
        cal = cal_fix_shift(cal, shift)

    # HD actually contains the GS length; convert to true HD.
    cal = cal_len_to_hd(cal)

else:
    cal = None

# Set up climate streamer
bin_reader = ClimateBinReader(
    data_dir=path_climate, 
    landmap_path=path_landmap, 
    climate_vars=climate_vars,
    file_years=binfile_years,
    file_template=climate_filename_template,
)

pixels = set(bin_reader.land_pixels())
pixels = sorted(pixels)

# Map lat/lon to pixel integer for faster processing downstream
pxmap = pl.DataFrame({
    "pixel": range(len(pixels)), 
    "lat": [x[0] for x in pixels], 
    "lon": [x[1] for x in pixels]
})

loc_data = loc_data.join(pxmap, on=["lat", "lon"])
pxmap = loc_data[["pixel", "lat", "lon"]]

px_iterator = ClimateBinIterator(pxmap, bin_reader, year_from, year_to, block_size=1000)
blocks = []
for climate in tqdm(px_iterator):

    px_chunk = climate.select("pixel").unique().join(pxmap, on="pixel")
    block = climate.join(loc_data, on="pixel").join(co2, on="year")

    if ssp == "historical":
        block_2015 = (
            read_climate_2015(px_chunk)
            .join(loc_data, on="pixel")
            .join(co2, on="year")
        )
        block = pl.concat([block, block_2015], how="vertical").sort(["pixel", "year", "day"])
    
    # Overwrite HD/PD with calendar NetCDF values
    if cal is not None:
        block = block.join(
            cal,
            on=["lat", "lon", "year"],
            how="left",
            suffix="_cal",
        ).with_columns([
            pl.coalesce(["pd_cal", "pd"]).alias("pd"),
            pl.coalesce(["hd_cal", "hd"]).alias("hd"),
        ]).drop(["pd_cal", "hd_cal"])

    # Convert units
    block = block.with_columns(
        pl.col("hurs") / 100,  # % -> ratio
        pl.col("pr") * 24 * 60 * 60,  # kg/m²/s -> mm/day; 1 kg of rain water spread over 1 square meter of surface is 1 mm in thickness
        pl.col("rsds") * 60 * 60 * 24 / 1e6,  # W/m² -> MJ/m²/day
        pl.col("tasmax") - 273.15,  # K -> °C
        pl.col("tasmin") - 273.15,  # K -> °C
    ).with_columns(
        tav = (pl.col("tasmax") + pl.col("tasmin")) / 2
    )

    block = process_climate_features(
        block, 
        crop=crop, 
        calculate_hd="no" if cal_mode == "nc_pd_hd" else "with_fallback"
    )
    blocks.append(block)

# Finalize df
df = (
    pl.concat(blocks, how="vertical")
    .join(pxmap, on="pixel")
    .drop("pixel", "gs")
)

if ssp == "historical":
    df = df.filter(pl.col("yr") < 2015)

df = compress(df)

df.write_parquet(path_out)

print("done")
