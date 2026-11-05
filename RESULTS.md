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

## Real data: historical Uganda district case anomalies

Windows CPU, Python 3.14.4 and NumPy 2.5.4. Source: [Tompkins et al. (2019), PANGAEA supplement 2](https://doi.pangaea.de/10.1594/PANGAEA.897624), CC BY 4.0. The archive contains published monthly case anomalies for 56 districts. Observations repeat across ensemble leads, so preparation selects a single copy and uses only the previous month's and year-ago anomalies relative to the forecast date. Training outcomes precede January 2009, and test forecast dates begin in January 2009. Rows that cross the cutoff are omitted.

| Horizon | Train rows | Test rows | Ridge MAE / RMSE | Persistence MAE / RMSE | Training mean MAE / RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1 month | 2,016 | 1,288 | 0.383 / 0.516 | 0.391 / 0.538 | 0.976 / 1.152 |
| 4 months | 1,848 | 1,120 | 0.719 / 0.905 | 0.783 / 1.006 | 0.991 / 1.169 |

Persistence predicts the last observed anomaly for that district. Errors are in the archive's published anomaly units. This is a retrospective baseline on the publisher's normalized series, which assumes prior observations were available at the forecast date. The archive provides no time-stamped releases or official outbreak labels, and the split evaluates later periods in districts seen during training.

| Other source | Status |
| --- | --- |
| [Makerere/Lacuna smartphone microscopy](https://doi.org/10.7910/DVN/VEADSE) | Dataverse v5 metadata lists the Uganda thin-smear archive (about 730 MB). Before training, verify annotation coverage for both classes and obtain slide or participant group identifiers. |
| [ClinEpiDB PRISM](https://clinepidb.org/ce/app/record/dataset/DS_0ad509829e) | Follow-up requires the participant and repeated-measure exports, a defined future outcome, and a split with disjoint groups. No cohort export was used in this run. |
| [Uganda DHIS2](https://malariajournal.biomedcentral.com/articles/10.1186/s12936-024-04838-w) | Operational outbreak evaluation requires an authorized weekly extract and prespecified outbreak thresholds. |

Microscopy and cohort data address different outcomes. Security evaluation still requires benign application logs and labeled attack replays.
