"""Functional coverage model for the Project 1 FWFT FIFO (cocotb-coverage).

Coverpoints and crosses follow vplan.md section 3 (C01-C04, C07, C08, C10,
C11, X01, X02). Sampling uses only the public interface and the reference
model's PRE-edge and POST-edge state -- never RTL internals.

The model only RECORDS. It never fails a test, so it cannot break the
graded mutation run. Closure is judged from the report it writes.

Use (from a cocotb test):
    cov = FifoCoverage(depth=8, width=8)
    cov.sample_cycle(occ_pre, wr, rd, data, acc_wr, acc_rd, occ_post)
    cov.sample_reset(occ_pre, wr)
    cov.report(dut._log, seed)
"""
import os

from cocotb_coverage.coverage import CoverCross, CoverPoint, coverage_db

REPORT_DIR = os.path.dirname(os.path.abspath(__file__))

# Bin labels (DEPTH-independent; the sampler maps numbers onto them).
OCC = ["empty", "one", "middle", "near_full", "full"]                 # C01
REQ = ["idle", "read", "write", "both"]                              # C02
ACC = ["none", "read_only", "write_only", "both"]                    # C03
TRANS = ["empty_to_one", "one_to_empty", "near_full_to_full",        # C04
         "full_to_near_full", "hold_empty", "hold_full", "hold_interior"]
DATA = ["all_zero", "all_one", "alternating", "other"]               # C07
BURST = ["single", "short", "long"]                                  # C08
WRAP = ["write_wrap", "read_wrap"]                                   # C10
RESET = ["reset_no_request", "reset_plus_write"]                     # C11

# X02 ignore bins: combinations the spec makes impossible.
#   empty: nothing can be read, so read_only / both can never be accepted.
#   full:  nothing can be written, so write_only / both can never be accepted.
X02_IGNORE = [("empty", "read_only"), ("empty", "both"),
              ("full", "write_only"), ("full", "both")]


# ---- coverpoints (CoverPoints must be declared above the crosses using them)
@CoverPoint("fifo.occupancy", xf=lambda s: s["occ"], bins=OCC)
@CoverPoint("fifo.request", xf=lambda s: s["req"], bins=REQ)
@CoverPoint("fifo.accepted", xf=lambda s: s["acc"], bins=ACC)
@CoverPoint("fifo.transition", xf=lambda s: s["trans"], bins=TRANS)
@CoverCross("fifo.occ_x_request", items=["fifo.occupancy", "fifo.request"])
@CoverCross("fifo.occ_x_accepted", items=["fifo.occupancy", "fifo.accepted"],
            ign_bins=X02_IGNORE)
def _cycle(s):
    pass


@CoverPoint("fifo.write_data", xf=lambda d: d, bins=DATA)
def _write_data(d):
    pass


@CoverPoint("fifo.write_burst", xf=lambda b: b, bins=BURST)
def _write_burst(b):
    pass


@CoverPoint("fifo.read_burst", xf=lambda b: b, bins=BURST)
def _read_burst(b):
    pass


@CoverPoint("fifo.pointer_wrap", xf=lambda w: w, bins=WRAP)
def _wrap(w):
    pass


@CoverPoint("fifo.reset", xf=lambda r: r, bins=RESET)
def _reset(r):
    pass


class FifoCoverage:
    """Turns per-cycle numbers into bin labels and samples the model."""

    def __init__(self, depth=8, width=8):
        self.depth = depth
        self.mask = (1 << width) - 1
        self.alt = {int("01" * width, 2) & self.mask,   # 0x55 for WIDTH=8
                    int("10" * width, 2) & self.mask}   # 0xAA for WIDTH=8
        self.wr_run = self.rd_run = 0                    # request burst lengths
        self.wr_total = self.rd_total = 0                # logical write/read index
        self.cycles = 0
        self.closed_at = None        # first cycle at which every bin was hit
        self.first_hit = {}          # "item:bin" -> cycle it was first hit

    # -- label helpers --------------------------------------------------------
    def occ(self, n):
        if n == 0:
            return "empty"
        if n == self.depth:
            return "full"
        if n == 1:
            return "one"
        if n == self.depth - 1:
            return "near_full"
        return "middle"

    def trans(self, pre, post):
        d = self.depth
        table = {(0, 1): "empty_to_one", (1, 0): "one_to_empty",
                 (d - 1, d): "near_full_to_full", (d, d - 1): "full_to_near_full",
                 (0, 0): "hold_empty", (d, d): "hold_full"}
        if (pre, post) in table:
            return table[(pre, post)]
        if pre == post:
            return "hold_interior"
        return "other"                                   # not a C04 bin

    def data(self, v):
        if v == 0:
            return "all_zero"
        if v == self.mask:
            return "all_one"
        if v in self.alt:
            return "alternating"
        return "other"

    @staticmethod
    def burst(n):
        return "single" if n == 1 else ("short" if n < 8 else "long")

    # -- sampling -------------------------------------------------------------
    def _track(self):
        """Every 10 cycles: note newly hit bins and the cycle coverage closes."""
        self.cycles += 1
        if self.closed_at is not None or self.cycles % 10:
            return
        for name in coverage_db:
            item = coverage_db[name]
            if name == "fifo" or not hasattr(item, "detailed_coverage"):
                continue
            for b, hits in item.detailed_coverage.items():
                if hits and f"{name}:{b}" not in self.first_hit:
                    self.first_hit[f"{name}:{b}"] = self.cycles
        top = coverage_db["fifo"]
        if top.coverage == top.size:
            self.closed_at = self.cycles

    def _flush(self, wr, rd):
        if not wr and self.wr_run:
            _write_burst(self.burst(self.wr_run))
            self.wr_run = 0
        if not rd and self.rd_run:
            _read_burst(self.burst(self.rd_run))
            self.rd_run = 0

    def sample_cycle(self, occ_pre, wr, rd, data, acc_wr, acc_rd, occ_post):
        """One non-reset cycle: requests, model-predicted accepts, occupancy."""
        _cycle({
            "occ": self.occ(occ_pre),
            "req": REQ[(wr << 1) | rd],
            "acc": ACC[(int(acc_wr) << 1) | int(acc_rd)],
            "trans": self.trans(occ_pre, occ_post),
        })
        if acc_wr:
            _write_data(self.data(data))
            self.wr_total += 1
            if self.wr_total % self.depth == 0:
                _wrap("write_wrap")
        if acc_rd:
            self.rd_total += 1
            if self.rd_total % self.depth == 0:
                _wrap("read_wrap")
        self._flush(wr, rd)
        self.wr_run += wr
        self.rd_run += rd
        self._track()

    def sample_reset(self, occ_pre, wr):
        """A synchronous reset edge (security/trust corner when wr=1)."""
        self._flush(0, 0)
        _reset("reset_plus_write" if wr else "reset_no_request")
        self.wr_total = self.rd_total = 0                # pointers restart
        self._track()

    def finish(self):
        self._flush(0, 0)

    # -- report ---------------------------------------------------------------
    def report(self, log, seed):
        self.finish()
        top = coverage_db["fifo"]
        holes = []
        for name in sorted(coverage_db):
            item = coverage_db[name]
            if name == "fifo" or not hasattr(item, "detailed_coverage"):
                continue
            for b, hits in item.detailed_coverage.items():
                if hits == 0:
                    holes.append(f"{name}:{b}")
            log.info(f"COV {name:<22} {item.cover_percentage:6.2f}%  "
                     f"({item.coverage}/{item.size})")
        log.info(f"COV TOTAL seed={seed}  {top.cover_percentage:.2f}%  "
                 f"({top.coverage}/{top.size} bins)")
        log.info("COV HOLES " + (", ".join(holes) if holes else "none"))
        log.info(f"COV CLOSED_AT cycle={self.closed_at}")
        last = sorted(self.first_hit.items(), key=lambda kv: -kv[1])[:5]
        log.info("COV LAST_BINS_HIT " + ", ".join(f"{k}@{c}" for k, c in last))
        coverage_db.export_to_yaml(
            filename=os.path.join(REPORT_DIR, "coverage_report.yml"))
        coverage_db.export_to_xml(
            filename=os.path.join(REPORT_DIR, "coverage_report.xml"))
        return top.cover_percentage, holes
