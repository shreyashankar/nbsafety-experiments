#!/usr/bin/env ipython3
# -*- coding: utf-8 -*-
from functools import wraps
from io import StringIO
from IPython import get_ipython
from pprint import pprint

import argparse
import ast
import copy
import logging
import numpy as np
import nbsafety.safety
import pandas as pd
import random
import re
import signal
import sqlite3
import sys
import typing

# Context manager to capture output
class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio  # free up some memory
        sys.stdout = self._stdout


class TimeoutException(Exception):
    pass


def timeout(seconds=10):
    def decorator(func):
        def _handle_timeout(signum, frame):
            logging.error("Timed out")

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
            if "pylab" not in line and (
                "time" not in line or "timedelta" in line
            ):
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
    #     cell_source = f"""
    # try:
    # {cell_source}
    # except Exception as e:
    #     print(e)
    #     success = False"""
    return cell_source.strip()


def run_reactively(
    safety: nbsafety.safety.NotebookSafety,
    cell_id: int,
    successful_execs: dict,
) -> typing.Set[int]:
    """
    Simulates running `cell_id` and all dependent cells reactively.
    If there are multiple valid dependent cells, runs them in increasing order of cell id.

    Returns: the ids of all cells that were run (including `cell_id`).
    """
    executed_cells = set()
    prev_fresh_cells = set(
        safety.check_and_link_multiple_cells()["fresh_cells"]
    )
    fresh_cells = {cell_id}
    while len(fresh_cells) > 0:
        cell_id = next(iter(sorted(fresh_cells)))
        # cell = successful_execs[cell_id]
        cell = safety.cell_content_by_cell_id[cell_id]
        timeout_run_cell(cell_id, cell, safety=safety)
        executed_cells.add(cell_id)
        cell_id, cell = None, None
        cur_fresh_cells = set(
            safety.check_and_link_multiple_cells()["fresh_cells"]
        )
        new_fresh_cells = cur_fresh_cells - prev_fresh_cells
        prev_fresh_cells = cur_fresh_cells
        fresh_cells |= new_fresh_cells
        fresh_cells -= executed_cells
    return executed_cells


@timeout(seconds=30)
def timeout_run_cell(cell_id, cell_source, safety=None):
    if safety is None:
        get_ipython().run_cell(cell_source, silent=True)
        return False
    else:
        safety.set_active_cell(cell_id, position_idx=cell_id)
        get_ipython().run_cell_magic(safety.cell_magic_name, None, cell_source)
        return safety.test_and_clear_detected_flag()


def run_cells(cell_num_to_code):
    safety = nbsafety.safety.NotebookSafety.instance(
        cell_magic_name="_NBSAFETY_STATE",
        skip_unsafe=False,
        store_history=False,
        mark_stale_symbol_usages_unsafe=False,
    )
    successful_execs = {}
    all_cell_counter = 1
    cells_ran = []
    cells_parsed = []

    for cell_num, code in cell_num_to_code.items():
        try:
            ast.parse(code)
            cells_parsed.append(cell_num)
        except:
            pass
    # with Capturing() as output:
    for cell_num in cells_parsed:
        code = cell_num_to_code[cell_num]

        if cell_num == max(cells_parsed):
            # Capture output and split cell into two if there is > 1 line.
            with Capturing() as output:
                code = code.split("\n")
                code = ["\n".join(code[:-1]), code[-1]]
                try:
                    for c in code:
                        if c.strip() == "":
                            continue

                        timeout_run_cell(all_cell_counter, c, safety=safety)
                        if cell_num not in cells_ran:
                            cells_ran.append(cell_num)
                        successful_execs[all_cell_counter] = c
                        all_cell_counter += 1
                except:
                    pass

        else:
            try:
                timeout_run_cell(all_cell_counter, code, safety=safety)
                cells_ran.append(cell_num)
                successful_execs[all_cell_counter] = code
                all_cell_counter += 1
            except:
                pass

    # Pick a cell to randomly rerun and compute dependencies
    cell_to_rerun = random.choice(list(successful_execs))
    print(f"Cell to rerun: {cell_to_rerun}")
    # print(successful_execs[cell_to_rerun])
    # print(safety.cell_content_by_cell_id[cell_to_rerun])

    # print(successful_execs)
    # print(
    #     {
    #         cell_id: safety.cell_content_by_cell_id[cell_id]
    #         for cell_id in safety.cell_content_by_cell_id.keys()
    #     }
    # )

    cell_deps = sorted(run_reactively(safety, cell_to_rerun, successful_execs))
    cell_deps = {
        cell_id: safety.cell_content_by_cell_id[cell_id]
        for cell_id in cell_deps
    }
    print(cell_deps)

    slice_size = len(cell_deps.keys())
    slice_cells = "\n".join(cell_deps.values())

    # Filter out whitespace
    slice_cells = [
        elem for elem in slice_cells.split("\n") if elem.strip() != ""
    ]
    num_lines_in_slice = len(slice_cells)

    return (
        cells_ran,
        slice_size,
        num_lines_in_slice,
        slice_cells,
        cell_to_rerun,
    )


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
        group.sort_values(by=["counter"], ascending=True)[
            ["counter", "source"]
        ]
        .set_index("counter")
        .to_dict()["source"]
    )
    cell_num_to_code = modify_all_cell_source(cell_num_to_code)
    (
        all_successful_execs,
        slice_size,
        num_lines_in_slice,
        slice_cells,
        cell_to_rerun,
    ) = run_cells(cell_num_to_code=cell_num_to_code)

    # Write out to file
    f = open("eda/forward/results/nbsafety_stats.txt", "a+")
    f.write(
        str(
            (
                trace_id,
                session_id,
                all_successful_execs,
                cell_to_rerun,
                slice_size,
                num_lines_in_slice,
            )
        )
    )
    f.write("\n")
    f.close()

    # Write out slice
    f = open(f"eda/forward/results/nbsafety/{trace_id}_{session_id}.txt", "w+")
    f.write("\n".join(slice_cells))
    f.close()


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
