# R150 build

`ghost.html` is the page served by the one relay that still answers. To stand the challenge up, deploy it (and nine blank-status decoy pages) as subdomains under `northernlights.gg`, each with a real TLS certificate so the names appear in the public Certificate Transparency logs. Players find the names in CT, probe each, and read the ghost.
