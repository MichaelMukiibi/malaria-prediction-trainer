# Architecture

| Path | Responsibility |
| --- | --- |
| `trainer.py` | CSV validation, CPU training and evaluation, and run output |
| `plot_run.py` | Convert a run's metrics and loss history into PNG and SVG charts |
| `demo.py` | Deterministic synthetic images and tables for smoke checks |
| `prepare_pangaea.py` | Convert the published Uganda district anomaly ZIP into a dated forecast manifest |
| `prepare_makerere.py` | Read phone-camera labels and create a diagnostics manifest from verified split groups |
| `requirements*.txt` | CPU dependencies and the optional Isolation Forest dependency |
| `data/` | Local data and CSV manifests |
| `runs/` | Local metrics and model weights |

All modes take a prepared CSV and a fresh output directory. Explicit split assignments make the cohort reviewable before training. Each JSON report records the manifest digest and the runtime. For research runs, retain hashes of the source images and transformation code alongside the manifest.

Diagnostics downsamples RGB images to 16 × 16 and fits logistic regression. This is a low-cost image classification baseline. It compares pooled training, independent client models, and simulated federated averaging on the same holdout. Each round starts clients from the same global weights and averages their updates by client sample count. All clients run in one process. The output distinguishes relative accuracy change from percentage-point change. The desktop timer covers image loading, preprocessing, and inference for a single image. Completion fraction counts inference requests in that run.

Forecast uses ridge regression with a training-mean baseline. Follow-up uses logistic regression with a majority-class baseline. Both standardize on training data and require training outcomes to precede the first test prediction date. Follow-up additionally enforces disjoint participant or household groups. The weights file has three rows for these modes: coefficients plus intercept, feature means plus a placeholder zero, and feature standard deviations plus a placeholder one. Follow the feature order in the JSON report.

Security fits Isolation Forest on benign events and reports detection sensitivity, false positives, and the confusion counts on held-out scenarios. A deployment needs a separate policy that takes action on a flag and produces a log of whether the attempted operation was blocked. See the [Isolation Forest API](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html).

Phone inference, secure peer-to-peer updates, and active blocking need their own integration and verification. For phone benchmarking, export the chosen model to [LiteRT](https://developers.google.com/edge/litert), verify prediction parity, and run the device protocol in RESULTS.md.
