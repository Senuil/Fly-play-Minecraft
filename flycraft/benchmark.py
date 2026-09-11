import argparse
import json
import platform
import time
import numpy as np
from .controller import Controller


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--bundle')
    p.add_argument('--mapping')
    p.add_argument('--steps', type=int, default=100)
    args = p.parse_args()
    if args.steps < 1 or (args.bundle and not args.mapping):
        p.error('positive steps and mapping required for bundle')
    c = Controller(args.bundle, args.mapping)
    durations, action = [], None
    for _ in range(args.steps):
        started = time.perf_counter()
        action = c.step({'drive':1., 'obstacle_left':1., 'obstacle_right':0.})
        durations.append((time.perf_counter()-started)*1000)
    w = c.model.w
    print(json.dumps({'platform':platform.platform(), 'cpu':platform.processor(), 'mode':c.mode,
        'neurons':c.model.n, 'edges':w.nnz, 'steps':args.steps, 'backend':'scipy-cpu',
        'sparse_matrix_bytes':w.data.nbytes+w.indices.nbytes+w.indptr.nbytes,
        'p50_ms':float(np.percentile(durations,50)), 'p95_ms':float(np.percentile(durations,95)),
        'simulated_over_wall':50*args.steps/sum(durations), 'last_action':action}, indent=2))


if __name__ == '__main__':
    main()
