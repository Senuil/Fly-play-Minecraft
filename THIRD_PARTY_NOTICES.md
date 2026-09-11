# Sources and third-party notices

Neural equations and constants reference Philip Shiu and Nico Spiller's
[Drosophila brain model](https://github.com/philshiu/Drosophila_brain_model),
published with [Shiu et al., Nature 2024](https://doi.org/10.1038/s41586-024-07763-9).
Its MIT notice is preserved in `SHIU_LICENSE.txt`.
This implementation is a simplified independent engineering model with differences
documented in `docs/model.md`; it is not an endorsed or validated reproduction.

`fixtures/probe/weights.npz` and `ids.json` contain an induced six-neuron subset
of the upstream `Connectivity_783.parquet` and `Completeness_783.csv` files.
Connection weights are scaled by 0.275 mV, duplicate edges aggregated, and all
edges between the selected neurons retained. The I/O mapping is newly assigned
for software testing and does not claim anatomical function.
Source hashes and transformations are recorded in `fixtures/probe/metadata.json`.

Credit for the underlying connectome belongs to the FlyWire Consortium:
[Dorkenwald et al., Neuronal wiring diagram of an adult brain, Nature 2024](https://doi.org/10.1038/s41586-024-07558-y).
The original [FlyWire data archive](https://zenodo.org/records/10676866) and
[FlyWire portal](https://home.flywire.ai/) retain their applicable data terms;
this project does not relicense the underlying data or third-party components.

Mineflayer and Flying Squid are PrismarineJS projects distributed under MIT;
their dependencies retain their own package licenses. NumPy and SciPy are BSD
licensed; PyArrow is part of Apache Arrow. Dependencies are installed separately
and are not bundled in this deliverable.

No implementation code from Eon's GPL-licensed repository is included.
Minecraft is a Mojang/Microsoft product. This is an independent experimental
project and includes no Mojang server binary, client assets or account credentials.
