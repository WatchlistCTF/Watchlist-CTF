# F400: Mirror Sites (solution)

> Spoilers below. Try [`../challenge.md`](../challenge.md) first.

## Flag

```text
number{the_clouds_do_not_speak_to_each_other_but_we_do}
```

## In short

One file was read from Google Cloud, staged in AWS and mirrored to Azure, and it was renamed at every hop. File names cannot link the three, but the file's MD5 hash is recorded in all three clouds. Each cloud also attached a small metadata fragment to the object. Find the object in each cloud, recover the three fragments (two of them from things the engineer "deleted"), and join them in the order the data moved.

## Walkthrough

1. Unpack the archive. Each cloud folder has three parts: an audit log, an access or usage log, and a storage inventory.
2. Start with the audit logs (CloudTrail, Azure Activity, GCP Admin Activity) and notice that they are no help. They only record management actions like creating buckets and changing permissions. They never record anyone reading or writing an object.
3. Switch to the logs that do record object activity: GCP storage usage logs, S3 server access logs, and Azure StorageBlobLogs. There are over 100,000 rows between them, which is too many to read by eye.
4. Find the common object by its fingerprint. Every inventory records an MD5 for each object: `md5Hash` in GCP (base64), `ETag` in AWS (hex), `Content-MD5` in Azure (base64). Convert them all to hex and intersect the three sets. Exactly one hash appears in all three: `c47f74a1d55cf905790b9c97b4640730`.
5. That one hash has three different names:
   - GCP: `exports/2026/q4/nl_client_roster_2026Q4.xlsx`
   - AWS: `staging/tmp/ds_0917.bin`
   - Azure: `archive/backup_final.dat`
6. Build the timeline for those three names from the access logs, with every timestamp converted to UTC. The night reads: read from GCP at 23:51, upload to AWS at 00:19, check at 01:33, copy to Azure at 01:58, then an overwrite in AWS at 02:11 and a delete in Azure at 02:15 to cover the tracks. The order of travel is GCP, then AWS, then Azure.
7. Collect the fragment (`mfrag` metadata) from each cloud:
   - GCP: it is on the object in the inventory.
   - AWS: the bucket has versioning. The current version is the harmless overwrite, and its fragment is fake. The older, non-current version has the matching hash and the real fragment.
   - Azure: the blob was soft-deleted. It is still listed in the inventory with `Deleted=True`, and its metadata holds the fragment.
8. Base64-decode the three fragments: `the_clouds_do_not_`, `speak_to_each_other_` and `but_we_do`. Join them in travel order inside `number{}`.

## Watch out for

- Time zones. The Azure blob logs are in UTC, but the Azure inventory shows local time with a minus seven hour offset. Convert everything to UTC before comparing.
- The current AWS version is a planted wrong answer. Its fragment decodes to something believable that is not part of the flag.
- Management audit logs are the first place most people look, and here they are a dead end by design.
- GCP also records a second checksum, `crc32c`. Only GCP has it, so it cannot link the three clouds. MD5 is the one value all three share.
- The night crosses midnight UTC. If you filter the logs by a single date you lose half the story.

## Solver

[`solve_f400.py`](solve_f400.py) walks the same six stages and checks each one, 18 checks in all.

- Unpack the challenge file from [`../files/`](../files/) first, then pass the `nl-incident-2026/` folder to the script.
- It needs only the Python 3 standard library. No network access or live server is needed.
- It knows none of the answers in advance. It finds the shared hash, the three names, the order of travel and the fragments from the data, and only the final flag is compared with a fixed value.
- We also rebuilt the whole package from the original creator scripts. All 115 files came out byte-for-byte identical to the released ones, and the solver passes 18 of 18 on both.
