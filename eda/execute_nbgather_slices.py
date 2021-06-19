# For each file in results/nbgather, execute the code in a subprocess

import os
import sys

files = os.listdir("results/nbgather")

for file in files:
    f = open(f"results/nbgather/{file}", "r+")
    code = f.read()

    pid = os.fork()

    if pid <= 0:
        code = (
            "import numpy as np; import pandas as pd; import matplotlib.pyplot as plt;\n"
            + code
        )
        exec(code)
        os._exit(0)

    pid, status = os.waitpid(pid, 0)
    status = os.WEXITSTATUS(status)

    # Log status info
    print("Child exited: pid %d returned %d" % (pid, status))
    srf = open("nbgather_slice_runs.txt", "a+")
    srf.write(f"{file}, {status}\n")
