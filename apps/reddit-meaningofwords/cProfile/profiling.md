# How I'm profiling the code

## Prerequisites

1. `pip install gprof2dot`

## Profiling

1. `python -m cProfile -o output.pstats main.py`
1. Stop the execution manually after a while (CTRL+C)
1. `gprof2dot -f pstats output.pstats| dot -Tpng -o cProfile/output.png`
