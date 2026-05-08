# Runtime Integration Guide

This guide describes the supported runtime integration patterns for the website generator.

## Supported runtime target

The generator supports runtime targets of type `django_service`.

Example target:

```yaml
runtime:
  targets:
    - name: commerce-api
      type: django_service
      public_base_url: http://localhost:8787
```

## Catalog snapshot workflows

Use runtime catalog snapshots to fetch runtime data at build time.

```yaml
runtime:
  catalog_snapshot:
    enabled: true
    target: commerce-api
    url_path: /catalog/snapshot
    output_dir: ./output/data/runtime
```

When enabled, the build will request the runtime target and write the retrieved data into the configured `output_dir`.

## Runtime-backed collections

Runtime-backed collections can be configured to render product catalogs or other API-driven content.

Example:

```yaml
content:
  collections:
    shop:
      type: runtime_catalog
      model: product
      route:
        prefix: shop
      layout: product
```

The runtime target must expose the expected schema and item model for the build to generate pages correctly.

## Django runtime companion

The bundled Django runtime app lives in `wg_runtime/`.

To start it locally:

```bash
python wg_runtime/manage.py migrate
python wg_runtime/manage.py createsuperuser
python wg_runtime/manage.py bootstrap_runtime_roles
python wg_runtime/manage.py runserver 127.0.0.1:8787
```

The runtime admin UI is available at `http://127.0.0.1:8787/admin/`.

## Runtime admin and order inspection

The runtime companion includes a Django admin interface for inspecting order, payment, and catalog state.

- Orders are read-only for audit purposes
- Inventory adjustments and product edits remain operational
- Runtime events can be replayed or requeued through admin tooling

## Check your runtime integration

- Confirm `public_base_url` points to a running runtime service
- Verify the runtime target responds successfully to the configured snapshot URL
- Run `wg build` and confirm runtime data is present in `output/data/runtime`
- Confirm theme templates can consume the runtime-backed collection data
