A CPU simulation comparing reactive DVFS with a predictive frequency controller. Both controllers use a FIFO queue and receive the same tasks.

Run

Use Python 3.14 with Tkinter for the interactive graph. Run these commands in the repository folder.

    python -m pip install numpy==2.3.5 matplotlib==3.10.8
    python run.py

The script opens the temperature and frequency graph, prints the comparison, and writes six raw CSV files plus summary_metrics.csv to the results folder.

To reproduce the paper's 11-seed check:

    python run.py --sensitivity

This writes results/seed_sensitivity.csv.

Experiment

The simulated core runs for 120 seconds in 10 ms steps. The main run uses seed 42 and three workloads with Poisson arrivals. The rates are 25 tasks/s for steady load, 9 tasks/s between bursts and 65 during bursts, and 49 tasks/s for sustained overload.
Reactive DVFS switches from 4 to 2 GHz at 95°C and returns to 4 GHz below 85°C. The predictive controller uses a 4.5-second thermal forecast with a 77°C target. Queue wait runs from arrival to first service and is reported for tasks that finish within the run. The model uses synthetic workloads and illustrative thermal parameters.
