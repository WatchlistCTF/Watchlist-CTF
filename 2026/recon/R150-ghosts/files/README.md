# R150 files

This challenge had no downloadable file. It ran against live infrastructure witnessed in Certificate Transparency.

## To stand it up again

- A set of relay subdomains under `northernlights.gg`, each with a real TLS certificate so it appears in the public CT logs. Nine are decoys with blank status pages; one ("the ghost") still serves a populated page carrying the flag.
- Players find the names in CT, probe each, and read the one that answers.
- The ghost page and decoys, and the deploy steps, will live in this challenge's `build/` folder.
