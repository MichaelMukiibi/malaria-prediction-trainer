# Malaria Prediction Trainer

A small Windows-friendly research repo for checking the experiments described in the ARDC malaria abstract. The training commands use a CPU and local files. The demo generates synthetic fixtures so you can check the pipeline before preparing real datasets.

## Run on Windows

Use 64-bit Python 3.14. Run these commands from the repository root in PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe demo.py
.\.venv\Scripts\python.exe trainer.py diagnostics --input data/demo/images.csv --out runs/demo-diagnostics
.\.venv\Scripts\python.exe trainer.py forecast --input data/demo/series.csv --features history --out runs/demo-forecast
.\.venv\Scripts\python.exe trainer.py followup --input data/demo/series.csv --features history --out runs/demo-followup
```

Install the optional dependency to evaluate Isolation Forest on event features.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-security.txt
.\.venv\Scripts\python.exe trainer.py security --input data/demo/events.csv --features rate errors --out runs/demo-security
```

Choose a fresh output directory for every run. Open its `metrics.json` to see the configuration, input manifest hash, environment, and metrics. Diagnostics, forecast, and follow-up also save NumPy weights.

## Plot run results

See [EDA.md](EDA.md) for the six exploratory figures and instructions to regenerate them from the local PANGAEA and Makerere archives.

Install `requirements-plots.txt` in the same environment as the trainer. Add `--plot` to any training command to save `charts.png` and `charts.svg` alongside `metrics.json`. To render or retitle an existing run, use:

```powershell
python -m pip install -r requirements-plots.txt
python plot_run.py runs/pangaea-h1/metrics.json --title "Uganda district anomalies | One-month forecast"
```

New diagnostic and follow-up runs record training loss, even when plotting is disabled. Older runs need to be rerun to recover a loss curve. Forecast and security figures show holdout metrics. See [REPORT.md](REPORT.md) for the charts and paper-ready results.

## Use research data

### Uganda district anomaly forecasts

Download the ZIP from the [PANGAEA source record](https://doi.pangaea.de/10.1594/PANGAEA.897624), or use the direct archive link below. The adapter reads the ZIP in place.

```powershell
New-Item -ItemType Directory -Force data | Out-Null
curl.exe --fail --location --output data/pangaea.zip https://store.pangaea.de/Publications/Tompkins-etal_2019/vectri_monthly_calibrated_timeseries_allyears_UGA_lneir_allLeads_repo.zip
foreach ($horizon in 1, 4) {
    python prepare_pangaea.py --archive data/pangaea.zip --horizon $horizon --out "data/pangaea-h$horizon"
    python trainer.py forecast --input "data/pangaea-h$horizon/forecast.csv" --features prior_anomaly year_ago_anomaly --persistence-feature prior_anomaly --out "runs/pangaea-h$horizon"
}
```

Use the virtual environment Python from the setup above if needed. Choose fresh output directories when repeating the commands. The adapter saves the archive hash, split date, and horizon in `source.json`. See [RESULTS.md](RESULTS.md) for the measured scores and the status of the other datasets.

### Other experiments

The [Makerere phone-camera archive](https://air.ug/downloads/plasmodium-phonecamera.zip) can be audited locally:

```powershell
python prepare_makerere.py --archive data/phonecamera.zip
```

When you have the verified slide or patient mapping, prepare the dataset and run diagnostics:

```powershell
python prepare_makerere.py --archive data/phonecamera.zip --groups data/makerere-groups.csv --out data/makerere
python trainer.py diagnostics --input data/makerere/images.csv --out runs/makerere
```

The grouping CSV needs `image,group,split,client`, with the JPG basename in `image`. Assign entire groups to a single split and client. The phone-camera archive comes from one hospital, so any subdivision into training clients is a simulation. If using a different Makerere release, check its layout and labels separately.

Prepare your own CSVs under `data/`. Keep a separate record of source version, preprocessing, data file hashes, cohort eligibility, and split assignments. The demo CSVs show the required layouts.

| Mode | Required CSV columns | Input preparation |
| --- | --- | --- |
| `diagnostics` | `image,label,split,group,client` | Use relative image paths within the manifest directory, binary labels, and a patient ID as the split group when available, or a slide ID when only slide grouping is possible. Keep all crops from each parent image in one split and check for duplicate images. Use at least two named training clients and both classes in each split. |
| `forecast` | `split,as_of,outcome_date,target` plus numeric features | Pick one horizon per run, use a numeric outcome such as district case anomaly, and compute features using only information available at `as_of`. |
| `followup` | `split,group,as_of,outcome_date,target` plus numeric features | Use a participant or household group, define an observable future outcome and horizon, and use binary targets. Keep both outcomes in each split. |
| `security` | `scenario,split,label` plus numeric features | Use benign training events and a held-out mix of benign and attack events. Group repeated events from the same scenario together. Select the contamination setting before scoring the test data. |

Use `train` and `test` as split names, ISO dates such as `2021-05-01`, and `--features` to name input predictors for the tabular and security commands. Run `python trainer.py --help` for options.

Candidate research sources are the [Ugandan smartphone microscopy collection](https://doi.org/10.7910/DVN/VEADSE), [PANGAEA district case anomalies](https://doi.pangaea.de/10.1594/PANGAEA.897624), [ClinEpiDB PRISM](https://clinepidb.org/ce/app/record/dataset/DS_0ad509829e), and an authorized [Uganda DHIS2 extract](https://malariajournal.biomedcentral.com/articles/10.1186/s12936-024-04838-w). For microscopy, review the annotation classes and completeness before defining image-level labels. Use PANGAEA for historical anomaly forecasting, and a surveillance series with a prespecified outbreak definition for outbreak evaluation. Keep the study protocol and dataset terms with the experiment records.

See [ARCHITECTURE.md](ARCHITECTURE.md) for model and split design, [RESULTS.md](RESULTS.md) for claim verification, and [CONTRIBUTING.md](CONTRIBUTING.md) for branch conventions.
