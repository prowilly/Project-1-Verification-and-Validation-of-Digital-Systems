"""Optional passive pin trace; does not alter stimulus, checks or coverage."""
import json
import os


def record_sample(observed, rst_n):
    path = os.environ.get('FIFO_TRACE_FILE')
    if path:
        row = {name: getattr(observed, name) for name in
               ('count', 'full', 'empty', 'rd_data', 'wr_en', 'rd_en', 'wr_data')}
        row['rst_n'] = rst_n
        with open(path, 'a') as stream:
            stream.write(json.dumps(row, sort_keys=True) + '\n')
