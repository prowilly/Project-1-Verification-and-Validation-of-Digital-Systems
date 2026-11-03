"""Project 1 directed baseline + HW4 regression, using layered modules.

Uses the original HW4 suite (historically 3/3 and 8/8 released mutants), plus
new directed tests for synchronous reset control overlap, idle/head holds and
all four key occupancy transitions. Project 1 results must be measured on Eustis.

Run on Eustis from ~/craft-vv-student/code:
    source /opt/course/cocotb-env/bin/activate
    just test fifo icarus
"""
import random
import cocotb

from fifo_bench import FifoBench

WIDTH = 8
DEPTH = 8
SEED = 0x4701


@cocotb.test()
async def test_fifo_directed_corners(dut):
    tb = await FifoBench.start(dut)

    # Underflow: read-only at empty is ignored. At empty, simultaneous r+w
    # accepts the write but cannot read the previously empty queue.
    await tb.cycle(rd_en=1, label="read while empty")
    await tb.cycle(rd_en=1, label="repeat empty read")
    await tb.cycle(wr_en=1, rd_en=1, wr_data=0xD3,
                   label="simultaneous at empty: only write is accepted")
    assert tb.scoreboard.model.count == 1
    await tb.cycle(rd_en=1, label="drain only item")
    assert tb.scoreboard.model.empty

    # Filling, overflow rejection, and full-boundary simultaneous operation.
    await tb.fill([0x00, 0x10, 0x55, 0x80, 0xFE, 0x7A, 0x22, 0xFF])
    assert tb.scoreboard.model.full
    await tb.cycle(label="idle while full")
    await tb.cycle(wr_en=1, wr_data=0xAA, label="write while full: dropped")
    await tb.cycle(wr_en=1, wr_data=0xBE, label="second rejected overflow")
    assert tb.scoreboard.model.count == DEPTH
    await tb.cycle(wr_en=1, rd_en=1, wr_data=0xAC,
                   label="simultaneous at full: read only, write dropped")
    assert tb.scoreboard.model.count == DEPTH - 1
    await tb.cycle(wr_en=1, wr_data=0x36, label="refill last slot")
    assert tb.scoreboard.model.full
    await tb.drain()
    assert tb.scoreboard.model.empty
    await tb.cycle(rd_en=1, label="over-read after complete drain")

    # At occupancy one, simultaneous r+w must replace the FWFT head now,
    # without a bubble, and without changing count.
    await tb.cycle(wr_en=1, wr_data=0x35, label="single entry")
    for data in (0xC1, 0x00, 0xFF, 0x72, 0x9B):
        await tb.cycle(wr_en=1, rd_en=1, wr_data=data,
                       label="simultaneous r+w at count one")
        assert tb.scoreboard.model.count == 1
    await tb.drain()

    # Simultaneous traffic in an interior occupancy, with nonidentical data.
    await tb.fill([0x14, 0x28, 0x3C, 0x50])
    for data in (0x64, 0x78, 0x8C, 0xA0, 0xB4):
        await tb.cycle(wr_en=1, rd_en=1, wr_data=data,
                       label="simultaneous r+w in interior")
        assert tb.scoreboard.model.count == 4
    await tb.drain()
    dut._log.info("Directed FIFO boundary tests and ordering checks passed")


@cocotb.test()
async def test_fifo_pointer_wrap_and_reset(dut):
    tb = await FifoBench.start(dut)

    # Maintaining count==DEPTH-1 ensures every simultaneous operation is
    # accepted; >4 complete revolutions of both read and write pointers.
    await tb.fill([0x30 + i for i in range(DEPTH - 1)])
    for i in range(4 * DEPTH + 9):
        await tb.cycle(wr_en=1, rd_en=1, wr_data=(i * 37 + 0x91) & 0xFF,
                       label="pointer wrap under simultaneous traffic")
        assert tb.scoreboard.model.count == DEPTH - 1
    await tb.drain()

    # Repeated full-depth fill/drain rounds wrap pointers even without overlap.
    for round_number in range(4):
        await tb.fill([((round_number << 5) ^ (i * 29)) & 0xFF
                       for i in range(DEPTH)])
        assert tb.scoreboard.model.full
        await tb.drain()
        assert tb.scoreboard.model.empty

    # A nonempty reset must flush state and restart pointers consistently.
    await tb.fill([0xDE, 0xAD, 0xBE, 0xEF, 0x42])
    await tb.reset()
    assert tb.scoreboard.model.empty
    await tb.fill([0x01, 0x02, 0x04, 0x08])
    await tb.drain()
    dut._log.info("Pointer wrap and midstream reset checks passed")


@cocotb.test()
async def test_fifo_seeded_random_interleave(dut):
    tb = await FifoBench.start(dut)
    rng = random.Random(SEED)

    # Bias toward full, then empty, then overlap, followed by mixed traffic.
    # This reliably reaches boundaries while preserving varied data ordering.
    phases = (
        (240, 0.80, 0.25, "write-biased random"),
        (240, 0.25, 0.80, "read-biased random"),
        (320, 0.80, 0.80, "overlap-biased random"),
        (400, 0.50, 0.50, "balanced random"),
    )
    for cycles, write_probability, read_probability, label in phases:
        for _ in range(cycles):
            wr_en = int(rng.random() < write_probability)
            rd_en = int(rng.random() < read_probability)
            wr_data = rng.getrandbits(WIDTH)
            await tb.cycle(wr_en, rd_en, wr_data, label=label)

    # Flush all surviving values: exposes latent data/order corruption.
    await tb.drain()
    await tb.cycle(rd_en=1, label="post-random empty read")
    dut._log.info("1,200 seeded randomized FIFO transactions passed; seed=%#x", SEED)


@cocotb.test()
async def test_fifo_idle_hold_and_flag_transitions(dut):
    """Cover 0->1, 7->8, 8->7, 1->0 and hold states with FWFT checks."""
    tb = await FifoBench.start(dut)

    for _ in range(3):
        await tb.cycle(label="idle when empty")
    await tb.cycle(wr_en=1, wr_data=0x55, label="empty to one (FWFT first word)")
    for _ in range(3):
        await tb.cycle(label="idle with valid head")

    await tb.fill([0x30 + i for i in range(DEPTH - 2)])
    assert tb.scoreboard.model.count == DEPTH - 1
    await tb.cycle(label="hold at near-full")
    await tb.cycle(wr_en=1, wr_data=0xC3, label="near-full to full")
    assert tb.scoreboard.model.full
    for _ in range(3):
        await tb.cycle(label="idle when full")
    await tb.cycle(rd_en=1, label="full to near-full")
    while tb.scoreboard.model.count > 1:
        await tb.cycle(rd_en=1, label="drain to one")
    await tb.cycle(label="hold at one")
    await tb.cycle(rd_en=1, label="one to empty")
    await tb.cycle(label="idle after draining")
    dut._log.info("Idle and key flag transition checks passed")


@cocotb.test()
async def test_fifo_synchronous_reset_with_requests(dut):
    """Check specified reset outputs on a clock edge with both enables high.

    A reset-time write request is a security/trust control combination. The
    spec requires the reset outputs but does not define a transfer on that edge.
    """
    tb = await FifoBench.start(dut)
    await tb.fill([0xD1, 0xE2, 0xF3])
    assert tb.scoreboard.model.count == 3
    await tb.reset(wr_en=1, rd_en=1, wr_data=0xA5)
    assert tb.scoreboard.model.empty
    await tb.cycle(wr_en=1, wr_data=0x87, label="first write after reset")
    await tb.cycle(label="hold new FWFT head")
    await tb.cycle(rd_en=1, label="first read after reset")
    assert tb.scoreboard.model.empty
    dut._log.info("Synchronous reset with asserted controls and recovery passed")
