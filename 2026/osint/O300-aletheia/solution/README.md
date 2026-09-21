# O300: Aletheia (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{forty_two_layers_of_aletheia}
```

## In short

The website was cleaned up, but the Wayback Machine kept a copy from before. The old copy links to a PDF, the PDF gives the address of a data file, and the data file is one small flag wrapped in 42 layers of compression and encoding. Some of those formats need tools you have to build from source.

## Walkthrough

### Find what was taken down

1. Visit `aletheia-research.github.io`. It looks clean.
2. Ask the Wayback Machine for everything it has under that site. The CDX search with a wildcard (`aletheia-research.github.io*`) lists every captured address.
3. Captures from 21 August 2026 include two pages that no longer exist: `press.html` and `reports/AR-2024-NL-disclosure.pdf`.
4. Open the archived `press.html`. It links to the PDF. Download the archived PDF and extract its text. It gives an address on the live site: `/data/artifact`.
5. Download `data/artifact`. It has no file extension.

### Dig to the floor

6. Identify the file by its first bytes, not by its name. It is gzip.
7. Decompress it, and identify the result the same way. It is another format. This repeats 42 times.
8. Do not do this by hand. Write a loop: read the first bytes, pick the matching tool, unpack, repeat until plain text comes out.
9. The layers include the usual formats (gzip, xz, bzip2, zstd, lz4, lzma, 7z, zip, tar, compress, base64) and uncommon ones (lzop, lzip, rzip, lrzip, arj, cab, ascii85). Layers 31 to 42 cycle through four formats that are not in normal package managers: zpaq, lzfse, bsc and snzip. You have to build those from source.
10. Some tar layers hold more than one file. One is bait that contains plain text, and the other is the next layer. Follow the one that is still compressed.
11. The last layer is a line of base64. Decode it for the flag.

## Watch out for

- File names and extensions inside the layers are misleading. Trust the first bytes only.
- The friction of installing tools is deliberate. The free hint on the board said as much: some of the tools are not in any package manager.

## Solver

[`o300_solve.py`](o300_solve.py) is a blind peeler. It reads the file, identifies each layer by its magic bytes (never by a file name), decompresses it with the matching tool, and repeats until it reaches the floor, where it decodes the base64 line to the flag. It knows no answer in advance.

- Give it the `data/artifact` file: `python3 o300_solve.py artifact`.
- It shells out to the compression tools, so they must be on your PATH. The apt ones are `gzip bzip2 xz zstd lz4 ncompress lzop lzip lrzip rzip arj cabextract gcab zip unzip p7zip-full`. Four more have to be built from source and put on the PATH: `zpaq`, `lzfse`, `bsc` (libbsc) and `snzip`. The header lists them.
- The artifact came from the live site and is not in this repo. Get it from the page it was linked from, or rebuild it (the build files regenerate the exact stack).
- We checked the peeler's engine with a simulation: a floor wrapped in 13 layers using the tools available, including the tar-decoy and the ascii85 gotcha. The unchanged solver peeled all 13 by magic byte, stepped past the decoy's bait file, and decoded the floor. The four build-from-source formats use the same file-in file-out pattern as the tools it was tested against.
