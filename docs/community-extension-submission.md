# DuckDB community-extensions submission notes

Copy the descriptor at `docs/community-extensions/open_data_duck/description.yml` to
`duckdb/community-extensions/extensions/open_data_duck/description.yml` when opening
the upstream community-extensions PR.

## Pinned source

The descriptor pins `nikmarch/open-data-duck` at:

```text
677b5418ab6b6f1c739a6083347dad2db16c1399
```

That is the post-Extension-7 `origin/main` commit that already contains the native
extension scaffold, embedded registry functions, sqllogictest coverage, Linux x64
extension distribution workflow, pre-community release workflow, and custom
extension repository bridge. The descriptor itself is submission paperwork, so the
buildable extension source does not depend on this notes PR.

## Community descriptor coverage

The descriptor fills the community-extensions fields used by existing descriptors:

- `extension.name`: `open_data_duck`
- `extension.description`: embedded open-data source recipe index
- `extension.version`: `0.1.0`
- `extension.language`: `C++`
- `extension.build`: `cmake`
- `extension.license`: `MIT`
- `extension.maintainers`: `nikmarch`
- `repo.github`: `nikmarch/open-data-duck`
- `repo.ref`: the pinned source commit above
- `docs.hello_world`: real `open_data_duck` functions only
- `docs.extended_description`: scope, API, network behavior, and platform limits

## Platform scope

The first community descriptor excludes every platform except Linux x64
(`linux_amd64`). That matches the current CI evidence: the Main Extension
Distribution Pipeline builds and smokes only `open_data_duck-v2.0.0-extension-linux_amd64`.

Excluded platforms in the descriptor:

```text
linux_arm64;linux_amd64_musl;linux_arm64_musl;osx_amd64;osx_arm64;windows_amd64;windows_arm64;windows_amd64_mingw;wasm_mvp;wasm_eh;wasm_threads
```

Add platforms only after their extension-distribution builds and smoke tests are
proven.

## API and network readiness

Community hello-world SQL intentionally uses only the current implemented API:

```sql
LOAD open_data_duck;
SELECT open_data_duck_ping();
SELECT id, source_type, status
FROM open_data_search('overture maps')
ORDER BY id
LIMIT 5;
SELECT open_data_sql('overture.maps.release');
```

It does not mention `open_data_table(...)` because that function is intentionally
not implemented yet.

Normal tests and descriptor checks must stay offline. The extension reads the
embedded registry only; public network access happens only when users execute a
returned recipe that loads `httpfs`, STAC, CKAN, Socrata, ArcGIS, or object-storage
queries.

## Local checks before upstream PR

Run these in this repository before copying the descriptor upstream:

```bash
uv run odd validate
uv run pytest
```

For native/community confidence, use the existing extension checks when the local
host has the DuckDB build toolchain and submodules ready:

```bash
git submodule update --init --recursive
make test-extension-sql
```

A full `duckdb/community-extensions` CI run still happens in the upstream PR. This
repo keeps the descriptor, pinned source, platform caveats, and offline acceptance
checks ready for that PR without pretending the extension is already signed by the
community repository.
