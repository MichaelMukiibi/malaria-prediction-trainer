# Results and reproduction status

The ARDC abstract reports the figures below. The attached manuscript gives the abstract without the experiment artifacts needed to reconstruct those figures.

| Reported claim | What this repo measures | Evidence needed to verify the claim |
| --- | --- | --- |
| 100% uptime during network blackouts | Desktop inference completion fraction | On a named phone and app build, define uptime and the blackout window, run a scripted network outage, and record attempted and completed workflows, failures, and elapsed outage time. |
| Under two seconds per patient | Desktop per-image p50, p95, and maximum | Time complete patient workflows on that phone, including input, all images per patient, preprocessing, inference, and result display. Record cold and warm runs and the per-patient maximum. |
| 14% diagnostic accuracy gain from federation | Absolute and relative change versus mean local accuracy, plus percentage points versus pooled training | Original model, data splits, client allocation, exact comparator, and whether the 14% is relative or percentage points. Report sample counts and uncertainty on the same held-out cases. |
| Complete data isolation | Single-process simulation of client weight averaging | Test the actual peer-to-peer implementation under a defined threat model. Inspect messages, node storage, authentication, and failure behavior. |
| 99.4% of simulated attacks identified and blocked | Isolation Forest flags, sensitivity, and false-positive rate | Held-out replay scenarios and attack counts. Measure blocked attacks divided by attempted attacks and record benign requests blocked by the deployed policy. |
| No smartphone battery degradation | Pending phone measurement | Repeated, matched device runs with and without monitoring. Record elapsed time, workload, energy, temperature, and the prespecified difference considered meaningful. |

The abstract title also names outbreak prediction and follow-up stratification. Its results paragraph gives no numerical outcomes for those tasks. The CSV baselines let you run distinct experiments once a surveillance target or longitudinal outcome is defined.

## Synthetic smoke run

Windows CPU, Python 3.14.4, NumPy 2.5.4, and Pillow 13.0.0. The generated images encode classes through pixel brightness. The tabular fixtures also contain an artificial signal.

| Run | Observed result |
| --- | --- |
| Diagnostics | 60 training images, 20 test images, three simulated clients. Pooled, local, and federated accuracy were all 100%, a federated gain of 0 percentage points. All 20 test requests completed. Desktop per-image p95 was 4.46 ms and maximum was 4.91 ms in the verification run. |
| Forecast | Ridge MAE 0.300 and RMSE 0.319. Training-mean baseline MAE and RMSE both 0.500. |
| Follow-up | Logistic accuracy 100%. Majority baseline accuracy 50%. |
| Security | Isolation Forest (scikit-learn 1.8.0) flagged all 10 synthetic attacks and 1 of 10 benign events. |

These numbers describe generated fixtures only. Record real-data and device results separately with the run configuration, source version, and split.
