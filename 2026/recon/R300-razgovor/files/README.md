# R300 files

This challenge had no single download. It was a four-hop chain across live services.

## To stand it up again, in order

1. A public GitHub repo (`decima-cloud/nl-relay-tools`) sanitized at HEAD, with a scrubbed secret still in its history.
2. An S3 bucket the history points to, holding a photo whose EXIF carries the next address.
3. A provenance API endpoint the photo points to, which returns the flag for the right node.

The seed repo, the bucket contents, the photo and the endpoint code will live in this challenge's `build/` folder.
