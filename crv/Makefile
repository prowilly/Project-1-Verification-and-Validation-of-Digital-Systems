# cocotb flow for the Project 1 constrained-random (pyvsc) FIFO regression.
#   make                          # Icarus, SEED=4701, N_CYCLES=5000
#   make SEED=17 N_CYCLES=8000    # any seed / length (seed is the source of truth)
#   make DUT=/path/to/fifo.sv     # override the DUT (used by the mutation harness)
TOPLEVEL_LANG ?= verilog
SIM           ?= icarus

DUT ?= $(CURDIR)/../dut/fifo.sv
VERILOG_SOURCES = $(DUT)
TOPLEVEL = fifo
MODULE   = test_fifo

SEED     ?= 4701
N_CYCLES ?= 5000
STIM     ?= biased
export SEED N_CYCLES STIM

# tb/ (driver/monitor/scoreboard/bench), lib/ (FifoModel), coverage/ (coverage model)
export PYTHONPATH := $(CURDIR):$(CURDIR)/../tb:$(CURDIR)/../lib:$(CURDIR)/../coverage:$(PYTHONPATH)

include $(shell cocotb-config --makefiles)/Makefile.sim
