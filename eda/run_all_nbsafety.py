import logging
import pandas as pd
import sqlite3
import subprocess

logging.basicConfig(level=logging.INFO)
distinct_trace_sessions = pd.read_csv("./data/sessions.csv").drop_duplicates()

# Read file
f = open("stats.txt", "r+")
lines = f.readlines()[1:]
lines = [line[1:-1].split(",") for line in lines]
processed_trace_sessions = [
    (int(line[0].strip()), int(line[1].strip())) for line in lines
]

for _, row in distinct_trace_sessions.iterrows():
    if int(row["trace"]) < 428:
        continue
    if (int(row["trace"]), int(row["session"])) in processed_trace_sessions:
        logging.info(
            f"trace {row['trace']}, session {row['session']} already processed"
        )
        continue
    command = f"ipython eda/run_nbsafety.py -- --trace={row['trace']} --session={row['session']}"
    logging.info(command)
    try:
        ret = subprocess.call(command, shell=True)
        if ret != 0:
            logging.warning(
                f"trace {row['trace']}, session {row['session']} got nonzero return code {ret}"
            )
    except Exception:
        logging.warning(
            f"trace {row['trace']}, session {row['session']} did not execute"
        )
