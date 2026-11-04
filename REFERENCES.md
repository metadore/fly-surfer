# References

## FlyWire data and connectome

FlyWire Consortium (Princeton University). *FlyWire Whole-brain Connectome
Connectivity Data*. Version 783.0. Zenodo, 2 June 2024.
DOI: [10.5281/zenodo.10676866](https://doi.org/10.5281/zenodo.10676866).
License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

Dorkenwald, S., Matsliah, A., Sterling, A. R., et al. (FlyWire Consortium).
"Neuronal wiring diagram of an adult brain." *Nature* **634**, 124-138 (2024).
DOI: [10.1038/s41586-024-07558-y](https://doi.org/10.1038/s41586-024-07558-y).

Schlegel, P., Yin, Y., Bates, A. S., et al. "Whole-brain annotation and
multi-connectome cell typing of Drosophila." *Nature* **634**, 139-152 (2024).
DOI: [10.1038/s41586-024-07686-5](https://doi.org/10.1038/s41586-024-07686-5).

Zheng, Z., Lauritzen, J. S., Perlman, E., et al. "A Complete Electron
Microscopy Volume of the Brain of Adult Drosophila melanogaster." *Cell*
**174**, 730-743.e22 (2018).
DOI: [10.1016/j.cell.2018.06.019](https://doi.org/10.1016/j.cell.2018.06.019).

FlyWire. *Codex connectome browser and data download portal*.
<https://codex.flywire.ai/> (accessed 2026-11-04). The portal publishes the
citation requirements and Terms of Service that apply to downloads from Codex.

## Modelling and numerical methods

Gerstner, W., Kistler, W. M., Naud, R., & Paninski, L. *Neuronal Dynamics:
From Single Neurons to Networks and Models of Cognition*. Cambridge University
Press (2014). DOI:
[10.1017/CBO9781107447615](https://doi.org/10.1017/CBO9781107447615).
Online edition: <https://neuronaldynamics.epfl.ch/online/index.html>.

The simulator uses an exact exponential-Euler update for the passive LIF
membrane, threshold/reset, a quantised refractory period and a configuration
membrane floor. Those choices are described in the root `README.md` and in
`configs/neuron_config.yaml`; they are model assumptions, not measured fly
physiology.

## Software

Harris, C. R., Millman, K. J., van der Walt, S. J., et al. "Array programming
with NumPy." *Nature* **585**, 357-362 (2020).
DOI: [10.1038/s41586-020-2649-2](https://doi.org/10.1038/s41586-020-2649-2).

McKinney, W. "Data Structures for Statistical Computing in Python."
*Proceedings of the 9th Python in Science Conference* (SciPy 2010), 56-61.

Hunter, J. D. "Matplotlib: A 2D graphics environment." *Computing in Science &
Engineering* **9**(3), 90-95 (2007).
DOI: [10.1109/MCSE.2007.55](https://doi.org/10.1109/MCSE.2007.55).

Package versions and licenses are listed in `requirements.txt` and
`THIRD_PARTY_NOTICES.md`.

## Provenance note

The 15 raw FlyWire files were downloaded before this repository was created.
No download log or source URL was stored with them. The local version is
inferred as v783 from an incomplete download filename; row counts, checksums
and reconstructed totals are consistent with the v783 release, but the
inference is not attested by the completed files. See
`datasets/manifest.json` and `datasets/README.md` before republishing the raw
data or claiming a specific release.

## Citing this repository

No archived release or `CITATION.cff` has been created yet, and no project-wide
source licence has been selected. Until those exist, cite the repository URL
and the exact commit hash used. The underlying FlyWire data must still be
attributed separately under its CC BY 4.0 terms.
