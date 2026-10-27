# Contributing

Changes that alter descriptor definitions, CrystalNN/BV/SMACT behavior, pair
rules, feature policy, scaling, kNN distance, or the contrast definition must
be treated as a new representation version and must not silently overwrite the
canonical paper model.

Before submitting a change:

1. install the locked development environment;
2. run `pytest -q` and `cifmagfilter self-test`;
3. run `python scripts/check_repository.py`;
4. update `DESCRIPTORS.md`, `paper/METHODS.md`, manifests and changelog if the
   scientific representation changes;
5. never commit source datasets, API keys, credentials, local absolute paths,
   generated caches or historical development ZIPs.
