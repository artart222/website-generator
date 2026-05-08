# Release Checklist

This checklist captures the acceptance criteria and smoke tests for a Phase 6 hardening release.

## Build and CI readiness

- [ ] `pytest` passes on supported Python versions
- [ ] `ruff format --check .` passes
- [ ] `ruff check .` passes without new errors
- [ ] `python -m mypy core wg_runtime extensions plugins` passes
- [ ] CI definitions include Ubuntu and Windows runners, and Python 3.10 plus 3.12

## Documentation readiness

- [ ] `docs/DEVELOPER_GUIDE.md` accurately describes architecture, extension points, and build lifecycle
- [ ] `docs/USER_GUIDE.md` covers install, build, serve, and content authoring workflows
- [ ] `docs/MIGRATION_GUIDE.md` documents config migration and runtime compatibility checks
- [ ] `docs/EXTENSION_AUTHOR_GUIDE.md` documents extension manifest and registration hooks
- [ ] `docs/THEME_AUTHOR_GUIDE.md` documents theme package structure and overrides
- [ ] `docs/RUNTIME_INTEGRATION_GUIDE.md` documents runtime target setup and catalog snapshot expectations

## Runtime smoke tests

- [ ] Django runtime companion can be started with `python wg_runtime/manage.py runserver`
- [ ] Runtime admin is reachable at `http://127.0.0.1:8787/admin/`
- [ ] Catalog snapshot target returns valid JSON
- [ ] `wg build` generates runtime snapshot contents under `output/data/runtime`

## Release approvals

- [ ] Release notes or change summary are prepared
- [ ] Documentation links are present in `README.md`
- [ ] Code quality workflow is configured and badges are up to date
- [ ] Regression tests for runtime integration and extension loading are included
