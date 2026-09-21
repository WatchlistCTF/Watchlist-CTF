# O300 build

`o300_build.py` wraps a base64 flag floor in 42 layers of compression and encoding, common formats outside, rare ones (zpaq, lzfse, bsc, snzip) at the core. It needs the same toolchain as the solver, including the four built from source. `artifact` is the built reference file the solver peels.

O300 was a live challenge: the artifact was served from `aletheia-research.github.io` (with the pre-scrub page in the Wayback Machine). The reference `artifact` here lets the solver run offline.
