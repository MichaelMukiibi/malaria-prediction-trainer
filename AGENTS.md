# Repository instructions

Keep the default training path runnable from PowerShell on a Windows CPU. Use local files and preserve the command-line interface described in README.md.

Before changing model inputs or evaluation, review ARCHITECTURE.md and RESULTS.md. Preserve held-out groups and chronological boundaries. Fit preprocessing and decision thresholds on training or validation data. Keep synthetic smoke checks separate from research results and deployment measurements.

Keep raw data, private logs, trained weights, and generated runs out of Git. Use `feat/`, `doc/`, and `fix/` branches according to CONTRIBUTING.md. Run the relevant synthetic command before integrating changes and record the dataset version, split, baseline, and hardware when reporting a result.
