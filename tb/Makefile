# Layered cocotb FIFO baseline.
#   make            # run with Icarus (default)
#   make SIM=icarus # run with Icarus Verilog
#   make DUT=/path/to/fifo.sv   # override the DUT (used by the mutation harness)
TOPLEVEL_LANG ?= verilog
SIM           ?= icarus

DUT ?= $(CURDIR)/../dut/fifo.sv
VERILOG_SOURCES = $(DUT)
TOPLEVEL = fifo
MODULE   = test_fifo

export PYTHONPATH := $(CURDIR)/../lib:$(PYTHONPATH)

include $(shell cocotb-config --makefiles)/Makefile.sim
