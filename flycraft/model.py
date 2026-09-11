"""Sparse LIF model; mV and ms units. Not a validated Shiu reproduction."""
import numpy as np
from scipy import sparse


class LIF:
    def __init__(self, weights, seed=7, dt_ms=0.1):
        self.w = sparse.csr_matrix(weights, dtype=np.float32)
        if self.w.shape[0] != self.w.shape[1] or not np.isfinite(self.w.data).all():
            raise ValueError("weights must be square and finite (post, pre)")
        if dt_ms not in (0.1, 0.2):
            raise ValueError("dt_ms must exactly resolve 1.8 ms delay and 2.2 ms refractory")
        self.dt = dt_ms
        self.n = self.w.shape[0]
        self.seed = seed
        self.reset()

    def reset(self):
        self.rng = np.random.default_rng(self.seed)
        self.v = np.full(self.n, -52., dtype=np.float32)
        self.g = np.zeros(self.n, dtype=np.float32)
        self.refractory = np.zeros(self.n, dtype=np.int32)
        self.delay = [np.zeros(self.n, dtype=np.float32) for _ in range(round(1.8/self.dt))]
        self.cursor = 0

    def advance(self, input_indices, input_hz, duration_ms=50):
        indices = np.asarray(input_indices, dtype=np.int64)
        hz = np.asarray(input_hz, dtype=np.float32)
        if indices.shape != hz.shape or np.any(indices < 0) or np.any(indices >= self.n):
            raise ValueError("invalid stimulus indices")
        if not np.isfinite(hz).all() or np.any(hz < 0) or np.any(hz > 500):
            raise ValueError("input rates must be finite and within 0..500 Hz")
        if not 0 < duration_ms <= 1000 or not np.isclose(duration_ms/self.dt, round(duration_ms/self.dt)):
            raise ValueError("invalid duration")
        counts = np.zeros(self.n, dtype=np.int32)
        for _ in range(round(duration_ms/self.dt)):
            self.g += self.delay[self.cursor]
            self.delay[self.cursor].fill(0)
            active = self.refractory == 0
            # Explicit Euler; both derivatives evaluated from previous state.
            self.v[active] += self.dt / 20 * (-52 - self.v[active] + self.g[active])
            self.g[active] *= 1 - self.dt / 5
            self.refractory[self.refractory > 0] -= 1
            events = self.rng.random(len(hz)) < -np.expm1(-hz*self.dt/1000)
            selected = indices[events]
            self.v[selected[active[selected]]] += 68.75
            spikes = active & (self.v > -45)
            counts += spikes
            self.v[spikes] = -52
            self.g[spikes] = 0
            self.refractory[spikes] = round(2.2/self.dt)
            # Ring slot is read again exactly delay_steps updates later.
            self.delay[self.cursor] += self.w @ spikes.astype(np.float32)
            self.cursor = (self.cursor + 1) % len(self.delay)
        return counts * (1000 / duration_ms)
