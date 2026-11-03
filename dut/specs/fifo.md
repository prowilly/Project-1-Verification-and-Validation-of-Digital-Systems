# FIFO specification (dut/fifo.sv)

A parameterized **synchronous, first-word fall-through (FWFT)** FIFO.

## Parameters
- `WIDTH` (default 8) — data width in bits.
- `DEPTH` (default 8) — capacity in entries.

## Ports
| Signal | Dir | Meaning |
|--------|-----|---------|
| `clk` | in | rising-edge clock |
| `rst_n` | in | active-low synchronous reset |
| `wr_en`, `wr_data` | in | request a write of `wr_data` |
| `rd_en` | in | request a read (pop) |
| `rd_data` | out | **head of the FIFO; valid whenever `!empty`** (FWFT) |
| `full`, `empty` | out | status flags |
| `count` | out | current occupancy, 0..DEPTH |

## Behavior (the contract)
1. **Reset:** while `rst_n==0`, on the next clock edge `count→0`, `empty=1`, `full=0`.
2. **Write:** a write occurs iff `wr_en && !full`. A write asserted while `full`
   is **dropped** (no overflow, no corruption).
3. **Read:** a read occurs iff `rd_en && !empty`. A read asserted while `empty`
   is **ignored** (no underflow). `rd_data` continuously shows the current head.
4. **Simultaneous read+write** (both enabled, not full, not empty): both happen
   on the same edge and `count` is **unchanged**.
5. **Flags:** `full == (count==DEPTH)`, `empty == (count==0)` at all times.
6. **Ordering:** strictly first-in-first-out.

## Corner cases a good testbench must hit
Fill to `full`; drain to `empty`; write-while-full (dropped); read-while-empty
(ignored); simultaneous r+w at the boundaries; pointer wrap-around; and the
ordering guarantee under random interleaving.
