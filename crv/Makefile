# Seeded pyvsc regression; defaults are the 8x8 submission configuration.
TOPLEVEL_LANG ?= verilog
SIM ?= icarus
DUT ?= $(CURDIR)/../dut/fifo.sv
VERILOG_SOURCES = $(DUT)
TOPLEVEL = fifo
MODULE = test_fifo
WIDTH ?= 8
DEPTH ?= 8
SEED ?= 4701
N_CYCLES ?= 5000
STIM ?= biased
RESET_DENOMINATOR ?= 200
REQUIRE_CLOSURE ?= 1
export WIDTH DEPTH SEED N_CYCLES STIM RESET_DENOMINATOR REQUIRE_CLOSURE
export PYTHONPATH := $(CURDIR):$(CURDIR)/../tb:$(CURDIR)/../lib:$(CURDIR)/../coverage:$(PYTHONPATH)
ifeq ($(SIM),icarus)
COMPILE_ARGS += -Pfifo.WIDTH=$(WIDTH) -Pfifo.DEPTH=$(DEPTH)
else ifeq ($(SIM),verilator)
COMPILE_ARGS += -GWIDTH=$(WIDTH) -GDEPTH=$(DEPTH)
endif
# Separate elaborations prevent stale binaries when the parameters change.
SIM_BUILD ?= sim_build/$(SIM)-$(WIDTH)x$(DEPTH)
include $(shell cocotb-config --makefiles)/Makefile.sim
