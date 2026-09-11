import json
from pathlib import Path
import numpy as np
from scipy import sparse
from .model import LIF

INPUTS = ("drive", "obstacle_left", "obstacle_right")
OUTPUTS = ("forward", "turn_left", "turn_right")


class Controller:
    def __init__(self, bundle=None, mapping=None, seed=7):
        if bundle is None:
            # Intentionally synthetic six-cell test fixture; NOT fruit fly data.
            weights = sparse.csr_matrix(([60., 60., 60.], ([3, 5, 4], [0, 1, 2])), shape=(6, 6))
            self.inputs = {k: [i] for i, k in enumerate(INPUTS)}
            self.outputs = {k: [i+3] for i, k in enumerate(OUTPUTS)}
            self.mode = "synthetic-demo"
        else:
            path = Path(bundle)
            weights = sparse.load_npz(path / "weights.npz")
            meta = json.loads((path / "metadata.json").read_text())
            ids = json.loads((path / "ids.json").read_text())
            if len(ids) != weights.shape[0] or len(set(ids)) != len(ids):
                raise ValueError("neuron IDs and weights disagree")
            if meta.get("orientation") != "post,pre":
                raise ValueError("unsupported matrix orientation")
            index = {str(value): i for i, value in enumerate(ids)}
            spec = json.loads(Path(mapping).read_text())
            if spec.get("dataset_version") != meta.get("dataset_version"):
                raise ValueError("mapping and connectome version must match")
            def groups(section, names):
                result = {}
                for name in names:
                    group = spec[section][name]
                    if not group or any(not isinstance(x, str) for x in group):
                        raise ValueError(f"{name}: provide nonempty root IDs as strings")
                    result[name] = [index[x] for x in group]
                    if len(set(result[name])) != len(result[name]):
                        raise ValueError("duplicate ID within group")
                return result
            self.inputs = groups("inputs", INPUTS)
            self.outputs = groups("outputs", OUTPUTS)
            incoming = {i for g in self.inputs.values() for i in g}
            outgoing = {i for g in self.outputs.values() for i in g}
            if incoming & outgoing:
                raise ValueError("input/output overlap would bypass neural propagation")
            if sum(map(len, self.inputs.values())) != len(incoming):
                raise ValueError("input groups must be disjoint")
            if sum(map(len, self.outputs.values())) != len(outgoing):
                raise ValueError("output groups must be disjoint")
            self.mode = "connectome-experimental"
        self.model = LIF(weights, seed=seed)
        self.filtered = dict.fromkeys(OUTPUTS, 0.)

    def reset(self):
        self.model.reset()
        self.filtered = dict.fromkeys(OUTPUTS, 0.)

    def step(self, observation):
        values = {}
        for name in INPUTS:
            value = observation[name]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be a finite number in [0,1]")
            values[name] = value
        indices, hz = [], []
        for name, group in self.inputs.items():
            indices.extend(group)
            hz.extend([values[name]*180] * len(group))
        rates = self.model.advance(indices, hz)
        for name, group in self.outputs.items():
            self.filtered[name] = 0.7*self.filtered[name] + 0.3*float(np.mean(rates[group]))
        left, right = self.filtered["turn_left"], self.filtered["turn_right"]
        return {
            "forward": self.filtered["forward"] >= 5,
            "yaw_rate": float(np.clip((left-right)/40, -1.5, 1.5)),
            "rates_hz": dict(self.filtered), "mode": self.mode,
            "simulated_ms": 50,
        }
