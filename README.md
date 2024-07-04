# Alpha Agent

The goal of this work is to build a comprehensive end-to-end alpha agent that has the capability to iteratively generate alpha strategies, backtest them on historical datasets, perform evaluations and consequently trade the alpha signals live if they exceed expected performance threshold.

### FIRST TASK

- Create a RAG over `101 alpha paper` to generate information like `alpha number, alpha expression and alpha explanation`.


from utils import save_output, SavePathType
from data_sources import FMPUtils