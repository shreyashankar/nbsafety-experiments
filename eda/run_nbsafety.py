#!/usr/bin/env ipython3
# -*- coding: utf-8 -*-
from functools import wraps
from IPython import get_ipython
from pprint import pprint

import argparse
import ast
import copy
import logging
import numpy as np
import nbsafety.safety
import pandas as pd
import re
import signal
import sqlite3
import sys


class TimeoutException(Exception):
    pass


def timeout(seconds=10):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutException()

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


IPYTHON_RE = re.compile(
    r"^("
    + "|".join(
        [
            r"get_ipython\(\)\.",
            r"ip\.",
            r"ipy\.",
        ]
    )
    + r")"
)

LINE_FILTER_RE = re.compile(
    r"^("
    + "|".join(
        [
            r"help\(",
            r"pdb\.",
            r"set_trace\(",
            r"ipdb\.",
        ]
    )
    + r")"
)


def get_df():
    conn = sqlite3.connect("./data/traces.sqlite", isolation_level=None)
    df = pd.read_sql_query(
        f"SELECT cell_execs.* from cell_execs",
        conn,
    )
    get_ipython().run_line_magic("matplotlib", "inline")
    get_ipython().run_cell("import numpy as np", silent=True)
    get_ipython().run_cell("import pandas as pd", silent=True)
    return df


def modify_cell_source(cell_source):
    lines = copy.deepcopy(cell_source.split("\n"))
    new_lines = []
    num_non_comment_lines = 0
    for line in lines:
        stripped = line.strip()
        match = IPYTHON_RE.match(stripped)
        if match is not None:
            if "pylab" not in line and ("time" not in line or "timedelta" in line):
                continue
        match = LINE_FILTER_RE.match(stripped)
        if match is not None:
            continue
        if not stripped.startswith("#"):
            num_non_comment_lines += 1
        new_lines.append("    " + line)
    cell_source = "\n".join(new_lines)
    if cell_source.strip() == "" or num_non_comment_lines == 0:
        return ""
    cell_source = f"""
try:
{cell_source}
except Exception as e:
    print(e)
    success = False"""
    return cell_source.strip()


@timeout(seconds=15)
def timeout_run_cell(cell_id, cell_source, safety=None):
    if safety is None:
        get_ipython().run_cell(cell_source, silent=True)
        return False
    else:
        safety.set_active_cell(cell_id, position_idx=cell_id)
        res = get_ipython().run_cell_magic(safety.cell_magic_name, None, cell_source)
        return safety.test_and_clear_detected_flag()


# ipython needs this
success = True


def run_cells(cell_num_to_code, verify_slicer=False):
    global success
    safety = nbsafety.safety.NotebookSafety.instance(
        cell_magic_name="_NBSAFETY_STATE", skip_unsafe=False, store_history=False
    )
    successful_execs = {}
    all_cell_counter = 1
    cells_ran = []
    for cell_num, code in cell_num_to_code.items():
        success = True

        try:
            ast.parse(code)
            timeout_run_cell(all_cell_counter, code, safety=safety)
            cells_ran.append(cell_num)
            successful_execs[all_cell_counter] = code
            all_cell_counter += 1
        except:
            success = False

        # if success:
        #     cells_ran.append(cell_num)
        #     successful_execs[all_cell_counter - 1] = code
        # else:
        #     if verify_slicer:
        #         print("FAILED!!!")
        #         print(code)

    if not verify_slicer:
        cell_deps = safety.get_cell_dependencies(len(successful_execs.keys()))

        slice_size = len(cell_deps.keys())
        # Verify dynamic slicer is can run without errors
        num_successful_execs_in_slice = run_cells(cell_deps, verify_slicer=True)
        return (cells_ran, num_successful_execs_in_slice, slice_size)

    return len(successful_execs.keys())


def modify_all_cell_source(cell_num_to_code):
    res = {}
    for cell_num, code in cell_num_to_code.items():
        code = modify_cell_source(code)
        if code == "":
            continue
        res[cell_num] = code
    return res


def run_func(trace_id, session_id, group):
    cell_num_to_code = (
        group.sort_values(by=["counter"], ascending=True)[["counter", "source"]]
        .set_index("counter")
        .to_dict()["source"]
    )
    cell_num_to_code = modify_all_cell_source(cell_num_to_code)
    all_successful_execs, num_successful_execs_in_slice, slice_size = run_cells(
        cell_num_to_code=cell_num_to_code
    )
    if num_successful_execs_in_slice != slice_size:
        logging.warning(
            f"Trace ID {trace_id}, session ID {session_id} had slice size {slice_size} but only {num_successful_execs_in_slice} cells in that slice successfully executed."
        )

    # Write out to file
    f = open("stats.txt", "a+")
    f.write(
        str(
            (
                trace_id,
                session_id,
                all_successful_execs,
                num_successful_execs_in_slice,
                slice_size,
            )
        )
    )
    f.write("\n")
    f.close()

    return (
        trace_id,
        session_id,
        all_successful_execs,
        num_successful_execs_in_slice,
        slice_size,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=int, default=31)
    parser.add_argument("--session", type=int, default=13)
    args = parser.parse_args()

    df = get_df()
    run_func(
        args.trace,
        args.session,
        df[(df["trace"] == args.trace) & (df["session"] == args.session)],
    )
