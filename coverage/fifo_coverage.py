"""Spec-based functional coverage, C01-C12 and X01-X05 in vplan.md.

Sample only after the scoreboard has checked the corresponding observation.
Each simulation owns one coverage database. Logical indices come from accepted
public-interface transactions, never the DUT's internal pointers.
"""
import json
import os
from itertools import product
from pathlib import Path

from cocotb_coverage.coverage import CoverCross, CoverPoint, coverage_db

WIDTH = int(os.environ.get("WIDTH", "8"))
DEPTH = int(os.environ.get("DEPTH", "8"))
CONFIG = f"{WIDTH}x{DEPTH}"
OCC = ["empty", "one", "middle", "near_full", "full"]
REQ = ["idle", "read", "write", "both"]
ACC = ["none", "read_only", "write_only", "both"]
TRANS = ["empty_to_one", "one_to_empty", "near_full_to_full",
         "full_to_near_full", "hold_empty", "hold_full", "hold_interior"]
FLAGS = ["empty", "interior", "full"]
HEAD = ["first_write_from_empty", "read_reveals_next",
        "simultaneous_replaces_one_entry", "idle_head_stable", "head_after_wrap"]
DATA = ["all_zero", "all_one", "alternating", "other"]
BURST = ["single", "short", "long"]
WRAP = ["no_wrap", "write_wrap", "read_wrap", "both_wrapped"]
RESET = ["initial_reset", "reset_when_nonempty", "post_reset_first_write"]
ORIGIN = ["initial_reset", "reset_when_nonempty"]
X02_IGNORE = [("empty", "read_only"), ("empty", "both"),
              ("full", "write_only"), ("full", "both")]
X03_PAIRS = dict(zip(TRANS, ["interior", "empty", "full", "interior",
                             "empty", "full", "interior"]))
# All reachable head-event pairs. An idle head is undefined at empty; a pop
# reveals an older next entry only when at least two entries existed pre-edge.
X04_PAIRS = ({("empty", HEAD[0]), ("one", HEAD[2])}
             | {(o, HEAD[1]) for o in ("middle", "near_full", "full")}
             | {(o, h) for o in OCC[1:] for h in (HEAD[3], HEAD[4])})


@CoverPoint("fifo.occupancy", xf=lambda s: s["occ"], bins=OCC)
@CoverPoint("fifo.request", xf=lambda s: s["req"], bins=REQ)
@CoverPoint("fifo.accepted", xf=lambda s: s["acc"], bins=ACC)
@CoverPoint("fifo.transition", xf=lambda s: s["trans"], bins=TRANS)
@CoverPoint("fifo.flags", xf=lambda s: s["flags"], bins=FLAGS)
@CoverCross("fifo.occ_x_request", items=["fifo.occupancy", "fifo.request"])
@CoverCross("fifo.occ_x_accepted", items=["fifo.occupancy", "fifo.accepted"],
            ign_bins=X02_IGNORE)
@CoverCross("fifo.transition_x_flags", items=["fifo.transition", "fifo.flags"],
            ign_bins=[(t, f) for t, f in product(TRANS, FLAGS) if X03_PAIRS[t] != f])
def _cycle(s):
    pass


# Called immediately after _cycle for this same checked transaction; its
# occupancy sample is therefore the pre-edge state of this head event.
@CoverPoint("fifo.head_event", xf=lambda event: event, bins=HEAD)
@CoverCross("fifo.occ_x_head", items=["fifo.occupancy", "fifo.head_event"],
            ign_bins=[p for p in product(OCC, HEAD) if p not in X04_PAIRS])
def _head(event):
    pass


@CoverPoint("fifo.write_data", xf=lambda value: value, bins=DATA)
def _write_data(value):
    pass


@CoverPoint("fifo.write_burst", xf=lambda value: value, bins=BURST)
def _write_burst(value):
    pass


@CoverPoint("fifo.read_burst", xf=lambda value: value, bins=BURST)
def _read_burst(value):
    pass


@CoverPoint("fifo.pointer_wrap", xf=lambda event: event, bins=WRAP)
def _wrap(event):
    pass


@CoverPoint("fifo.reset_scenario", xf=lambda event: event, bins=RESET)
def _reset_scenario(event):
    pass


@CoverPoint("fifo.reset_control", xf=lambda wr: "reset_plus_write" if wr else "reset_only",
            bins=["reset_only", "reset_plus_write"])
def _reset_control(wr):
    pass


@CoverPoint("fifo.recovery_origin", xf=lambda origin: origin, bins=ORIGIN)
@CoverCross("fifo.reset_x_first_accept", items=["fifo.recovery_origin", "fifo.accepted"],
            ign_bins=[(o, a) for o, a in product(ORIGIN, ACC) if a != "write_only"])
def _recovery(origin):
    pass


@CoverPoint("fifo.configuration", xf=lambda value: value, bins=[CONFIG])
def _configuration(value):
    pass


class FifoCoverage:
    def __init__(self, depth=DEPTH, width=WIDTH):
        if depth < 4 or width < 3:
            raise ValueError("This coverage partition requires DEPTH>=4 and WIDTH>=3")
        if (depth, width) != (DEPTH, WIDTH):
            raise ValueError("Set WIDTH/DEPTH before importing the coverage module")
        self.depth, self.width = depth, width
        self.mask = (1 << width) - 1
        self.alt = {int("01" * width, 2) & self.mask, int("10" * width, 2) & self.mask}
        self.wr_run = self.rd_run = 0
        self.wr_total = self.rd_total = 0
        self.both_wrapped = False
        self.pending_reset = None
        self.cycles = 0
        self.closed_at = None
        self.first_hit = {}
        self.checkpoints = []
        _configuration(CONFIG)

    def occ(self, n):
        return ("empty" if n == 0 else "full" if n == self.depth else
                "one" if n == 1 else "near_full" if n == self.depth - 1 else "middle")

    def trans(self, pre, post):
        d = self.depth
        table = {(0, 1): TRANS[0], (1, 0): TRANS[1], (d - 1, d): TRANS[2],
                 (d, d - 1): TRANS[3], (0, 0): TRANS[4], (d, d): TRANS[5]}
        return table.get((pre, post), TRANS[6] if pre == post else "other")

    def data(self, value):
        return ("all_zero" if value == 0 else "all_one" if value == self.mask else
                "alternating" if value in self.alt else "other")

    def burst(self, length):
        return "single" if length == 1 else "short" if length < self.depth else "long"

    def snapshot(self):
        items = {}
        holes = []
        for name in sorted(coverage_db):
            item = coverage_db[name]
            if not name.startswith("fifo.") or not hasattr(item, "detailed_coverage"):
                continue
            bins = {str(b): hits for b, hits in item.detailed_coverage.items()}
            items[name] = {"hit": item.coverage, "total": item.size, "bins": bins}
            holes.extend(f"{name}:{b}" for b, hits in bins.items() if not hits)
        top = coverage_db["fifo"]
        return {"hit": top.coverage, "total": top.size,
                "percentage": top.cover_percentage, "holes": holes, "items": items}

    def _track(self):
        snap = self.snapshot()
        for name, item in snap["items"].items():
            for b, hits in item["bins"].items():
                if hits:
                    self.first_hit.setdefault(f"{name}:{b}", self.cycles)
        if not snap["holes"] and self.closed_at is None:
            self.closed_at = self.cycles
        if self.cycles % 100 == 0:
            row = {k: snap[k] for k in ("hit", "total", "holes")}
            row["cycle"] = self.cycles
            if not self.checkpoints or self.checkpoints[-1]["cycle"] != self.cycles:
                self.checkpoints.append(row)

    def _flush(self, wr, rd):
        if not wr and self.wr_run:
            _write_burst(self.burst(self.wr_run))
            self.wr_run = 0
        if not rd and self.rd_run:
            _read_burst(self.burst(self.rd_run))
            self.rd_run = 0

    def sample_cycle(self, pre, wr, rd, data, acc_wr, acc_rd, observed):
        expected_wr, expected_rd = bool(wr and pre < self.depth), bool(rd and pre > 0)
        assert (bool(acc_wr), bool(acc_rd)) == (expected_wr, expected_rd), "bad acceptance sample"
        assert observed.count == pre + int(acc_wr) - int(acc_rd), "unchecked count sample"
        assert (observed.full, observed.empty) == (int(observed.count == self.depth),
                                                  int(observed.count == 0)), "bad flag sample"
        self.cycles += 1
        _cycle({"occ": self.occ(pre), "req": REQ[(wr << 1) | rd],
                "acc": ACC[(int(acc_wr) << 1) | int(acc_rd)],
                "trans": self.trans(pre, observed.count),
                "flags": "empty" if observed.empty else "full" if observed.full else "interior"})
        wr_wrap = rd_wrap = False
        if acc_wr:
            _write_data(self.data(data))
            self.wr_total += 1
            wr_wrap = self.wr_total % self.depth == 0
        if acc_rd:
            self.rd_total += 1
            rd_wrap = self.rd_total % self.depth == 0
        if wr_wrap:
            _wrap("write_wrap")
        if rd_wrap:
            _wrap("read_wrap")
        if not wr_wrap and not rd_wrap:
            _wrap("no_wrap")
        # Temporal milestone, NOT simultaneous pointer wraps (unreachable here).
        if not self.both_wrapped and min(self.wr_total, self.rd_total) >= self.depth:
            _wrap("both_wrapped")
            self.both_wrapped = True
        if pre == 0 and acc_wr:
            _head(HEAD[0])
        if pre >= 2 and acc_rd and observed.count:
            _head(HEAD[1])
        if pre == 1 and acc_wr and acc_rd:
            _head(HEAD[2])
        if pre > 0 and not wr and not rd:
            _head(HEAD[3])
        if rd_wrap and observed.count:
            _head(HEAD[4])
        if self.pending_reset and (acc_wr or acc_rd):
            assert acc_wr and not acc_rd, "first post-reset acceptance must be a write"
            _reset_scenario("post_reset_first_write")
            _recovery(self.pending_reset)
            self.pending_reset = None
        self._flush(wr, rd)
        self.wr_run += wr
        self.rd_run += rd
        self._track()

    def sample_reset(self, pre, wr, initial=False):
        if not initial:
            self.cycles += 1
        self._flush(0, 0)
        _reset_control(wr)
        origin = "initial_reset" if initial else "reset_when_nonempty" if pre else None
        if origin:
            _reset_scenario(origin)
            self.pending_reset = origin
        self.wr_total = self.rd_total = 0
        self.both_wrapped = False
        self._track()

    def report(self, log, seed, metadata, require_complete=True):
        self._flush(0, 0)
        self._track()
        report = self.snapshot()
        report.update({"seed": seed, "width": self.width, "depth": self.depth,
                       "cycles_sampled": self.cycles, "closed_at": self.closed_at,
                       "first_hit": self.first_hit, "checkpoints": self.checkpoints,
                       "require_complete": require_complete, **metadata})
        output = Path(os.environ.get("COVERAGE_DIR", Path(__file__).parent / "generated"))
        output.mkdir(parents=True, exist_ok=True)
        (output / "coverage.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        coverage_db.export_to_yaml(filename=str(output / "coverage.yml"))
        log.info(f"COV TOTAL seed={seed} {report['percentage']:.2f}% ({report['hit']}/{report['total']})")
        log.info(f"COV CLOSED_AT cycle={self.closed_at}; HOLES={report['holes']}")
        if require_complete:
            assert not report["holes"], "coverage target not reached: " + ", ".join(report["holes"])
        return report
