import json
import logging
import pandas as pd
import sqlite3
import subprocess

from pprint import pprint

logging.basicConfig(level=logging.INFO)
conn = sqlite3.connect("./data/traces.sqlite", isolation_level=None)
df = pd.read_sql_query(
    f"SELECT cell_execs.* from cell_execs",
    conn,
)
# distinct_trace_sessions = pd.read_csv("./data/sessions.csv").drop_duplicates()

# Read nbgather file
f = open("nbgather_stats.txt", "r+")
lines = f.readlines()[1:]
lines = [line[1:-1].split(",") for line in lines]
processed_trace_sessions = [
    (int(line[0].strip()), int(line[1].strip())) for line in lines
]

# Read nbsafety processed file
f = open("stats.txt", "r+")
lines = f.readlines()[1:]
lines = [line[1:-1].split(",") for line in lines]
nbsafety_processed_trace_sessions = {
    (int(line[0].strip()), int(line[1].strip())): ",".join(line[2:-4])[2:-1]
    for line in lines
}

for key, val in nbsafety_processed_trace_sessions.items():
    trace, session = key
    # valid_counters = [int(elem) for elem in val.split(",")]

    if (trace, session) in processed_trace_sessions:
        logging.info(f"trace {trace}, session {session} already processed")
        continue

    # # Grab code associated
    # specific_session = df[(df["trace"] == trace) & (df["session"] == session)]
    # print(specific_session.head(10))
    # # specific_session = specific_session.sort_values(by="counter", ascending=True)
    # # source_code = "\n".join(specific_session["source"].to_list())

    command = (
        f"node eda/nbgather/index.mjs {trace} {session} {json.dumps(val)}"
    )
    logging.info(" ".join(command.split(" ")[:4]))

    try:
        ret = subprocess.call(command, shell=True)
        if ret != 0:
            logging.warning(
                f"trace {trace}, session {session} got nonzero return code {ret}"
            )
    except Exception:
        logging.warning(f"trace {trace}, session {session} did not execute")
