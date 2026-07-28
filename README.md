# AGROMINDS

[![Tests](../../actions/workflows/tests.yml/badge.svg)](../../actions/workflows/tests.yml)

AGROMINDS generates annually resolved agro-meteorological indicators for
crop-specific growing seasons from daily climate data and crop calendars.

## Run a processing job

Install the dependencies, then create a local configuration and adjust its
machine-specific paths:

```bash
cp config.example.toml config.toml
```

Select the climate model, crop calendar, and scenario on the command line:

```bash
pip install -r requirements.txt
python generate_indicators.py --gcm GFDL-ESM4 --crop mai --ssp historical
```

`config.toml` contains paths only and is ignored by Git. The required arguments
are:

- `--gcm`: `GFDL-ESM4`, `IPSL-CM6A-LR`, `MPI-ESM1-2-HR`, `MRI-ESM2-0`,
  `UKESM1-0-LL`, or `GSWP3`
- `--crop`: `mai`, `ri1`, `ri2`, `soy`, or `swh`
- `--ssp`: `historical`, `ssp126`, `ssp245`, `ssp370`, `ssp585`, or `obsclim`

## Repository layout

- `generate_indicators.py`: user-facing processing command.
- `agrominds/`: reusable crop, biophysical, climate-I/O, feature, and pipeline
  code.
- `aux_data/`: small static inputs used by the current workflow.
- `notebooks/`: notebooks and figures used for data exploration and paper
  visualizations.
- `tests/`: automated tests and small test fixtures.
- `outputs/`: local processing outputs; excluded from version control.

The climate forcing data are external inputs and are not included in this
repository.

## Input data

`aux_data/` is a local, gitignored directory for third-party and
project-derived inputs. It is intentionally not distributed with the code.
See [input-data documentation](docs/input_data.md) for the required files,
authoritative sources, and provenance status.

## Reproducing manuscript figures

The notebooks in `notebooks/` reproduce the manuscript figures below. Install
the dependencies in `requirements.txt`, configure the output-data location in
`config.toml`, and run each notebook from the `notebooks/` directory.

| Notebook | Manuscript figure |
| --- | --- |
| `features_violins.ipynb` | Figure 2 |
| `features_lines.ipynb` | Figure 3 |
| `features_maps.ipynb` | Figure 4 |

These notebooks require the generated AGROMINDS Parquet outputs; they do not
recreate the full dataset from daily climate forcing.
