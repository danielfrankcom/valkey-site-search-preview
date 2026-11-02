# valkey.io site search: preview

**Preview:** <https://danielfrankcom.github.io/valkey-site-search-preview/>

An unofficial preview of the proposed site search for valkey.io, built from the `site-search` branch of
[danielfrankcom/valkey-io.github.io](https://github.com/danielfrankcom/valkey-io.github.io/tree/site-search) at the
commit pinned in [`pages.yml`](.github/workflows/pages.yml). This repository isn't an official Valkey project.

The workflow builds that commit with its own build action, the same one its deploy uses.
[`adapt-build.py`](adapt-build.py) is the only preview-specific step: it moves the site under this project path,
points the search box at the index there, removes analytics, and marks every page noindex.
