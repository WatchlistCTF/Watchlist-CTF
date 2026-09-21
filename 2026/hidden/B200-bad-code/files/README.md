# B200 files

This off-board challenge had no downloadable file. It was a page on the CTF domain.

## To stand it up again

- Serve `B200-badcode.html` at an unlisted path on the CTF site (`/badcode`). The page runs a scripted exchange and reveals the flag through a function called in the browser console.
- Players reach it by following the "signed: bad code" signature planted in other challenges (L100 and a cleanup script).
- The page will live in this challenge's `build/` folder.
