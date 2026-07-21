# Input data and provenance

AGROMINDS does not redistribute third-party input data. Place locally obtained
inputs in `aux_data/` (or update their paths in `config.toml`). Before making a
release, record the version, download date, checksum, and applicable licence
for every file used to generate a dataset release.

## Inputs referenced by the current workflow

| Local file or pattern | Role | Authoritative source / status |
| --- | --- | --- |
| `CLIMATE_LAT_PD_HD_PHU_ELEV_PRMT74_{crop}_noirr_fH_v3d.csv` | Crop-specific master location tables: coordinates, calendar dates, potential heat units, elevation, and PET parameters. | Project-derived input. These tables should not be redistributed until their complete build procedure and all upstream licences are documented. Their calendar component is derived from the GGCMI Phase 3 crop calendar. |
| `land-map.bin` | Mapping from the regular 0.5-degree grid to positions in climate binary files. | Source and generation procedure need to be confirmed and documented before release. |
| `co2_historical_annual_1765_2014.txt` | Historical annual atmospheric CO2 concentrations. | Source and version need to be confirmed and documented before release. |
| `spam2020_V2r2_global_A_allcrp_A_30mn.tif` | Cropland mask used by `generate_indicators.py`. | Obtain from the authoritative SPAM 2020 release. Confirm the release-specific licence and required citation before redistribution. |
| `spam2020_V2r2_global_H_MAIZ_A.tif` and derived 30 arcmin SPAM rasters | Harvested-area weights used in notebooks. | Obtain from the authoritative SPAM 2020 release. Confirm the release-specific licence and required citation before redistribution. |

The code also requires daily climate forcing, configured through
`isimip3b_root`, `obsclim_root`, and `reference_climate_root` in `config.toml`.
These inputs are external and are not stored in this repository.

## Crop calendars

The calendar inputs used here originate from the **GGCMI Phase 3 crop
calendar**, version 1.01. The authoritative record is
[Jägermeyr et al., 2021, Zenodo DOI 10.5281/zenodo.5062513](https://zenodo.org/records/5062513).
It provides rainfed and irrigated planting and maturity dates at 0.5-degree
resolution. The corresponding ISIMIP input-data records identify version
`20221024` and should be cited according to the original provider's policy.

## Data-release checklist

For every AGROMINDS release, add a release-specific inventory outside this code
repository (for example in the Zenodo data archive) containing:

1. Source URL or DOI, exact version, download date, and SHA-256 checksum for
   every external input.
2. The full build recipe for the master location tables and land map.
3. The licence, redistribution decision, and required citation for every input.
4. Checksums for the generated AGROMINDS output files.

Use only small, synthetic, redistributable fixtures under `tests/data/`.
