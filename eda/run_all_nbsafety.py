import logging
import pandas as pd
import sqlite3
import subprocess

logging.basicConfig(level=logging.INFO)
conn = sqlite3.connect("./data/traces.sqlite", isolation_level=None)
df = pd.read_sql_query(
    f"SELECT cell_execs.* from cell_execs INNER JOIN good_sessions ON cell_execs.trace == good_sessions.trace AND cell_execs.session == good_sessions.session",
    conn,
)
distinct_trace_sessions = df[["trace", "session"]].drop_duplicates()
print(distinct_trace_sessions)

# Read file
f = open("stats.txt", "r+")
lines = f.readlines()[1:]
lines = [line[1:-1].split(",") for line in lines]
processed_trace_sessions = [
    (int(line[0].strip()), int(line[1].strip())) for line in lines
]

for i, row in distinct_trace_sessions.iterrows():
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
