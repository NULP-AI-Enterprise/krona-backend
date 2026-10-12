# Search index initialization and repair

SentenceDocument declares `tokens` as `nested` and its form, lemma, POS and
morphology fields as `keyword`. Uploads alone do not install that mapping.
Elasticsearch's automatic mapping instead creates an ordinary object with text
fields, causing both concordance queries and word-list aggregations to fail.

Initialize the schema before accepting uploads:

```sh
python manage.py ensure_search_index
```

This installs an index template, creates a missing index, and validates an
existing index without deleting data. The Kubernetes migration init container
and the local setup scripts run this command. The updated init command requires
an image built from the code containing this management command; do not apply
the updated deployment manifest against an older image.

For a legacy incompatible index, first take an external backup, then run:

```sh
python manage.py ensure_search_index --repair
```

Repair temporarily blocks writes, copies the original index to a backup and a
new correctly mapped index, validates document counts and a nested aggregation,
then atomically switches `sentence_index` to a write alias. Failed validation
leaves the source in place and releases the temporary write block. Uploads
during the brief write block may fail and should be retried. Run one repair at
a time. Backup indexes remain available after repair.

Do **not** use `search_index --rebuild` to recover existing sentences: Postgres
contains text metadata, not uploaded content or processed sentences. The
real-time signal processor cannot regenerate that data.

## Production repair, 2026-10-12

- Replaced the dynamically mapped index with
  `sentence_index_v20261012115923_beb7d71e`, via the `sentence_index` alias.
- Preserved 707 documents and compared all IDs and source contents with
  `sentence_index_backup_20261012115923_beb7d71e`.
- Installed the schema template on the running Elasticsearch instance.
- Verified public word-list and concordance endpoints for an existing corpus
  and subcorpus, including lemma/POS filtering.
- External pre-repair export is on the operator's machine at
  `/Users/mac/krona-search-backups/sentence-index-before-repair-20261012.json`.

## Storage limitation

The current Kubernetes Elasticsearch deployment has no persistent volume.
Its data and templates can disappear when its pod is replaced. Do not roll out
Elasticsearch changes until its data has been backed up and a persistent-volume
migration/restore has been prepared. Installing a blank PVC alone does not
preserve the existing data. The repair above does not recreate that pod.
