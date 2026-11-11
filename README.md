# Algorithms Project - Task Scheduling (GA + Greedy Repair)

**Planned GitHub repository:** https://github.com/khaledAlzeer/task-scheduling-ga-greedy  
*The link will become active once the repository is created and the code is pushed.*


**Team:** Khaled Alzeer (202310298), Heba Alshawish (202310102), Mohammad Jaber (202312665)  
**Course:** Algorithms - Dr. Katrina  
**Phase 3:** Python Implementation and Initial Testing

## Problem

From tasks with fixed start and finish times, select the maximum number of non-overlapping tasks on a **single resource**, considering intervals `[start, finish)` so back-to-back jobs are allowed. Every task has equal priority. The decision vector contains 0/1 bits, and the objective is to maximize their sum subject to no overlaps.

The main evolutionary method is **binary Genetic Algorithm (GA)** with tournament selection, one-point crossover, bit-flip mutation, elitism, and deterministic **Greedy repair**. Classical earliest-finish Greedy is also computed as an **exact reference** for this standard unweighted model; the GA is not claimed to outperform it. The known reference optimum can be used to stop the search, but the exact solution is **not inserted** into the GA population.

## Files

| File | Purpose |
|---|---|
| `alg.py` | Complete optimization code, no UI dependencies: input checks, exact Greedy, feasibility repair, GA, metrics/history |
| `data_io.py` | Input formats, flexible column mapping, error messages, PTSP `.dat` parsing |
| `app.py` | Streamlit UI: choose file upload, manual entry, or included original dataset |
| `test_alg.py` | 12 automated unit tests for representation, fitness, repair, seed, and bad formats |
| `run_experiments.py` | Generates nine documented derived scenarios, runs three sizes + original, saves metrics and figures |
| `data/` | Original PTSP-derived CSV, nine labeled derived scenarios, manually verifiable example, metadata manifest |
| `figures/` | Labeled convergence plots and selected-job interval charts |
| `results/` | Initial results and environment/repeatability diagnostics |
| `requirements.txt` | Third-party dependencies |

## Setup

Python 3.10+ recommended, from VS Code, Spyder, or another Python IDE. **Locally verified on Windows / VS Code Git Bash with Python 3.13.6, pandas 2.3.3 and Matplotlib 3.11.2 (2026-11-11).** Use a project-specific virtual environment:

```sh
python -m venv .venv
# Windows Git Bash: source .venv/Scripts/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Start the user interface

```sh
python -m streamlit run app.py
```

1. Choose **Load a dataset file**, **Enter tasks manually**, or **Use included 111-task example**.
2. Upload `.csv`, `.tsv`, `.txt`, `.xlsx`, or original PTSP `.dat`. Common synonyms (`start`, `begin`, `end`, `finish`, `job`) are auto-recognized; headerless numeric pairs are accepted.
3. If column labels are unusual, select the correct columns using the three mapping dropdowns. Unknown columns are **not guessed**. Missing, invalid, duplicate or contradictory values produce an error rather than an invented result.
4. Change GA settings under the expander or use the documented Phase-2 defaults; select **Find an optimal-compatible schedule**.
5. View selected/unselected tasks, objective count, exact reference, gap, generations, execution time, convergence and interval plot. Download the selected jobs as CSV.

### Data format

Preferred CSV:

```csv
task_id,start_time,finish_time
A,1,3
B,2,5
C,3,4
```

Alternatives: `job,begin,end` as column names; 2-column headerless start/finish pairs (generated IDs); original PTSP `Jobs = N` `.dat` data with unrelated qualifications excluded. `.xlsx` first sheet is read. Numbers are in source time units; clock strings like `09:30` **are not** automatically assumed to be numerical times. All finish times must be greater than start times.

## Run Phase-3 tests and reproducible experiments

```sh
python -m unittest -v test_alg
python run_experiments.py
```

This recreates 9 derived datasets: `25`, `60`, `111` × `best`, `average`, `worst`, plus runs the unchanged original 111-task dataset. Best/average/worst describe **overlap density**, NOT theoretical runtime cases. All derived input variants preserve the original task IDs and durations but **change schedule positions**: do not present them as observations from PTSP. See `data/DATASET_MANIFEST.json` for source URL, exact source file, transformation, fixed seed, SHA-256 fingerprints, column definitions and known exact reference optima.

For the original 111-job PTSP extract, earliest-finish Greedy selects **T007, T036, T081**, so the exact maximum is **3**. For the six-task example, the known exact maximum is **4** (A, C, E, F). Measured runtimes will differ by computer even when the fixed-seed sequences agree.

## Phase 3: actual local test results (2026-11-11)

On the Windows / Git Bash test machine, the unit-test run reported **12 tests passed**, and `python run_experiments.py` reported **Repeatability (seed 42): True**. All 10 returned schedules were feasible. The table below records actual observations, not theoretical performance guarantees. Runtime varies by machine and run.

| Input profile | Tasks | GA selected | Exact Greedy optimum | Gap | Generations | Feasible |
|---|---:|---:|---:|---:|---:|---|
| 25-best | 25 | 25 | 25 | 0 | 14 | Yes |
| 25-average | 25 | 11 | 11 | 0 | 8 | Yes |
| 25-worst | 25 | 1 | 1 | 0 | 0 | Yes |
| 60-best | 60 | 58 | 60 | 2 | 100 | Yes |
| 60-average | 60 | 26 | 28 | 2 | 100 | Yes |
| 60-worst | 60 | 1 | 1 | 0 | 0 | Yes |
| 111-best | 111 | 100 | 111 | 11 | 100 | Yes |
| 111-average | 111 | 48 | 52 | 4 | 100 | Yes |
| 111-worst | 111 | 1 | 1 | 0 | 0 | Yes |
| 111-original-PTSP | 111 | 3 | 3 | 0 | 0 | Yes |

Additional user-interface checks completed locally: loading the original CSV, original PTSP `.dat`, headerless CSV, alternative column names, and Excel `.xlsx`; manual data entry; and rejecting missing numeric times and reversed intervals. These input checks were performed interactively, while the 12 unit tests are automated. The results CSV is in `results/phase3_results.csv`. The dataset transformations and provenance are documented in `data/DATASET_MANIFEST.json`.

**Figures:** `figures/convergence_25.png`, `convergence_60.png`, `convergence_111.png`, and `convergence_original.png` are generated by `run_experiments.py` from the recorded algorithm runs. The `figures/evidence_*.png` images are documentation aids; review them against the final code. For an instructor submission requiring real IDE or web-app screenshots, capture screenshots of the actual local run and label them accurately.

## GA implementation details

`run_genetic_algorithm()` uses population size `30`, maximum generations `100`, crossover `0.8`, mutation `0.05` per bit, initial-one probability `0.5`, tournament `3`, elite `1`, seed `42`. It maintains feasible candidate solutions via finish-time repair and stores the best-so-far fitness for each generation. The search halts if it hits the known exact optimum, or when the generation limit is reached. Result includes `GAResult` with selected IDs, rejected IDs, fitness, exact optimum, gap, generation count, evaluations, time, convergence history, stop reason and seed.

**Complexity:** globally sort tasks O(n log n) once; each repaired candidate scans n positions in O(n). For population P and G generations, time is O(n log n + G·P·n); memory is O(P·n + n), besides output history O(G). The exact Greedy baseline is computed as a reference because this standard problem has a known efficient optimal algorithm.

## Limitations and academic integrity

- This is not full personnel scheduling, weighted scheduling, dependency scheduling, multi-machine assignment, or a job-shop solver.
- Imported time columns must be numerical; ambiguous column names require a choice, and malformed rows are not silently discarded.
- Generated profiles are synthetic transformations of an academic benchmark. Source: Mathprog-ORlib PTSP, original archive `ptask.zip`, selected file `Data_10_51_111_66.dat`; https://andreas-ernst.github.io/Mathprog-ORlib/info/readmePTSP.html
- Experimental parameter tuning and statistical baseline comparisons are reserved for **Phase 4**.
- Update team-contribution statements in the PDF to reflect members' actual work before submission.


## GitHub and live deployment

The repository will contain the Python source, reproducible dataset transformations, tests, and example output figures after the initial push. Do not commit `.venv/`, credentials, or private data (see `.gitignore`).

From the project root, after creating an empty GitHub repository and activating the environment if needed:

```bash
git init
git branch -M main
git add .
git commit -m "Initial Phase 3 project"
git remote add origin https://github.com/khaledAlzeer/task-scheduling-ga-greedy.git
git push -u origin main
```

If the directory already has a Git repository or an `origin` remote, inspect `git status` and `git remote -v` before modifying either.

For Streamlit Community Cloud, connect the GitHub repository, select branch `main`, choose entrypoint `app.py`, and deploy. `requirements.txt` is in the repository root. The live web URL will be added here after successful deployment.

**Note:** The GitHub button in `app.py` points to the planned source repository URL. It will work after the repository exists and is publicly accessible; this is not the live application link.
