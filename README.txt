Comparison of a CPU simulator with a reactive DVFS and a predictive frequency controller. Controllers are equipped with the same FIFO queue and receive the same set of tasks.

Run

Python version 3.14 with Tkinter is required for the graph generation. To run the code execute the following commands in the repository folder.

    python -m pip install numpy==2.3.5 matplotlib==3.10.8
    python run.py

The code will open the temperature and frequency graph, print the comparison and write 6 raw CSV files as well as the summary_metrics.csv file in the results folder.

To repeat the seed sensitivity test from the paper (11 seeds):

    python run.py --sensitivity

This will write results/seed_sensitivity.csv.

Experiment

The CPU simulation runs for 120 seconds in 10 ms intervals. Main run uses seed 42 and three types of workload with Poisson distribution. Task generation rate is 25 tasks/s in steady state, 9 tasks/s between bursts and 65 during the bursts, and 49 tasks/s for overload. Reactive DVFS switches frequencies from 4 to 2 GHz if temperature is above 95° C and back to 4 GHz below 85° C. Predictive controller uses 4.5 second forecast and 77° C as optimal target temperature. Queue waiting time is measured from task generation
