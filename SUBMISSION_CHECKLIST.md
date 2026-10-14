# Submission Checklist and Folder Mapping

| Submission requirement | Location | Status |
|---|---|---|
| 1. Source code | [`src/`](src/) and [`scripts/`](scripts/) | Complete |
| 2. Dataset source/reference | [`data/README.md`](data/README.md) | Complete |
| 3. Preprocessing details | [`docs/PREPROCESSING.md`](docs/PREPROCESSING.md) | Complete |
| 4. README with instructions | [`README.md`](README.md) | Complete |
| 5. Experimental results | [`results/tables/`](results/tables/) | Complete |
| 6. Comparison plots | [`results/plots/`](results/plots/) | Complete |
| 7. Short report and Part F answers | [`docs/REPORT.md`](docs/REPORT.md) and [`README.md`](README.md) | Complete |
| Bonus: dynamic costs | [`results/bonus/`](results/bonus/) | Complete |
| Tests and validation | [`tests/`](tests/) | Complete |

## Recommended submission archive contents

Include everything except `.git/`, `.venv/`, `__pycache__/`, and the downloaded `data/raw/*.gz` archives. The evaluator can restore the official dataset with `python scripts/download_data.py` and reproduce all outputs with `python scripts/run_all.py`.

