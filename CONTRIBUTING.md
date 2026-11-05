# Contributing

Start work from an up-to-date `dev`. Commit on a topic branch, merge it into `dev` after checks pass, and push `dev` to `origin` with `git push origin dev`. Never commit directly to `main`. Use a pull request from `dev` to `main` for releases.

| Branch prefix | Use |
| --- | --- |
| `feat/` | Add a training, evaluation, or data preparation capability |
| `doc/` | Update the workflow, experiment design, or evidence notes |
| `fix/` | Correct training, data validation, or metrics behavior |

Keep commits focused. Run the README demo for the affected mode and inspect its metrics before integrating. For changes to input validation, also try an input that should fail. Check `git diff --check` before merging.

For empirical results, record the data release and permissions, grouping and split rules, preprocessing, run settings, and the hardware or software environment. Keep the untouched test split for final evaluation. Publish aggregate metrics only where the source permissions allow it.
