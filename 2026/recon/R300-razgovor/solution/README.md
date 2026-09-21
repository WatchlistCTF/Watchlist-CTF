# R300: Razgovor (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{provenance_outlives_the_cleanup}
```

## In short

A chain of four hops. Each thing they published still points at the next: a git commit points to a storage bucket, a photo in the bucket points to a web address in its metadata, and that address leads to an old API that hands over the flag.

## Walkthrough

1. Open the seed repository, `github.com/decima-cloud/nl-relay-tools`. The current files look clean.
2. Read the commit history. One commit is titled "chore: scrub secrets before public release". Git keeps the old version, so open that commit's diff.
3. The removed line is a setting, `RELAY_ARTIFACTS`, with the address of an S3 bucket: `nl-relay-artifacts-7c2a`.
4. Open the bucket address in a browser. It allows public listing. Most objects are about 1 KB. One stands out at 99 KB: `media/relay-cam-0419.jpg`.
5. Download the photo and read its metadata with `exiftool`. The User Comment field says `provenance:` followed by an address: `https://provenance.northernlights.gg/relay-export/`.
6. Visit that address and follow it to the legacy export API: `/relay-export/api/v2/legacy/export`. It wants to know which node. The bucket name already told you: `relay-7c2a`. Add `?node=relay-7c2a`.
7. The API answers with JSON that contains the flag.

## Watch out for

- Looking only at the repository's current files gets you nowhere. The leak is in the history.
- In the bucket, file size is the tell. Everything else is filler of about 1 KB.
