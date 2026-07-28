# Tests

Place only small, redistributable fixtures in `tests/data/`. The full climate
inputs and generated AGROMINDS outputs remain external to the repository.

`location_mai_minimal.csv` is a one-row fixture using the master-location CSV
schema. `test_feature_pipeline.py` combines it with synthetic daily climate
data to smoke-test feature generation, the final output schema, and
compression.
