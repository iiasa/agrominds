# Input data and provenance

AGROMINDS does not redistribute third-party input data. Place locally obtained
inputs in `aux_data/` (or update their paths in `config.toml`). Before making a
release, record the version, download date, checksum, and applicable licence
for every file used to generate a dataset release.

## Inputs referenced by the current workflow

| Local file or pattern | Role | Authoritative source / status |
| --- | --- | --- |
| `CLIMATE_LAT_PD_HD_PHU_ELEV_PRMT74_{crop}_{rf\|irr}.csv` | Crop-specific master location tables: coordinates, calendar dates, potential heat units, elevation, and PET parameters. | Dataset; cite Folberth et al. (2026)
| `land-map.bin` | Mapping from the regular 0.5-degree grid to positions in climate binary files. | Derived from CROMES v1.0; cite Folberth et al. (2025). |
| `co2_historical_annual_1765_2014.txt` | Historical annual atmospheric CO₂ concentrations. | ISIMIP3b climate-related forcing; cite Frieler et al. (2026). |
| `spam2020_V2r2_global_A_allcrp_A_30mn.tif` | Cropland mask used by `generate_indicators.py`. | SPAM 2020 Version 2.0 Release 2; cite IFPRI (2026). |
| `spam2020_V2r2_global_H_MAIZ_A.tif` and derived 30 arcmin SPAM rasters | Harvested-area weights used in notebooks. | SPAM 2020 Version 2.0 Release 2; cite IFPRI (2026). |

The code also requires daily climate forcing, configured through
`isimip3b_root`, `obsclim_root`, and `reference_climate_root` in `config.toml`.
These inputs are external and are not stored in this repository.

## Global crop parameter dataset

The crop-specific CSVs can be found on [https://doi.org/10.5281/zenodo.21790144](https://doi.org/10.5281/zenodo.21790144) 
and use the following structure. This example shows the
header and first five data rows of the maize table;
`CLIMATEID` identifies the climate-grid cell, `YLAT`/`XLON` are its centre
coordinates, `PLDOY`/`HRDOY` are planting and harvest day-of-year values, and
`PHU`, `ELEV`, `PRMT6`, and `PRMT74` are crop-model/PET inputs.

| CLIMATEID | YLAT | XLON | PLDOY | HRDOY | PHU | ELEV | PRMT6 | PRMT74 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 288348 | 83.75 | -36.25 | 152 | 283 | 200 | 1 | 1 | 1 |
| 289348 | 83.75 | -35.75 | 152 | 283 | 200 | 1 | 1 | 1 |
| 290348 | 83.75 | -35.25 | 152 | 283 | 200 | 1 | 1 | 1 |
| 291348 | 83.75 | -34.75 | 152 | 283 | 200 | 1 | 1 | 1 |
| 292348 | 83.75 | -34.25 | 152 | 283 | 200 | 56 | 1 | 0.7 |

## Data citations

- Folberth, C., Baklanov, A., Khabarov, N., Oberleitner, T., Balkovic, J., and
  Skalsky, R. (2025). *CROMES v1.0: A flexible CROp Model Emulator Suite for
  climate impact assessment – Frozen code repository and example for training
  EPIC-IIASA global gridded crop model emulators*. Zenodo.
  [https://doi.org/10.5281/zenodo.14901127](https://doi.org/10.5281/zenodo.14901127)

- Frieler, K., Lange, S., Schewe, J., Mengel, M., Treu, S., Otto, C.,
  Volkholz, J., Reyer, C. P. O., Heinicke, S., Jones, C., et al. (2026).
  Scenario set-up and the new CMIP6-based climate-related forcings provided
  within the third round of the Inter-Sectoral Model Intercomparison Project
  (ISIMIP3b, group I and II). *Geoscientific Model Development, 19*(10),
  4095–4135.
  [https://doi.org/10.5194/gmd-19-4095-2026](https://doi.org/10.5194/gmd-19-4095-2026)

- International Food Policy Research Institute (IFPRI) (2026). *Global
  Spatially-Disaggregated Crop Production Statistics Data for 2020 Version 2.0
  Release 2* (Version V6). Harvard Dataverse.
  [https://doi.org/10.7910/DVN/SWPENT](https://doi.org/10.7910/DVN/SWPENT)

- Folberth, C., Balkovic, J., Skalsky, R.& Oberleitner, T. (2026). *Global crop 
  parameter dataset for AGROMINDS* [Dataset]. Zenodo. 
  [https://doi.org/10.5281/zenodo.21790144](https://doi.org/10.5281/zenodo.21790144)

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
