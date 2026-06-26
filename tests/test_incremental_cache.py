"""Tests for the opt-in incremental build cache."""

from __future__ import annotations

from pathlib import Path

from core.build_cache import BuildCache, compute_build_signature


def test_unchanged_page_is_detected(tmp_path: Path):
    cache = BuildCache(tmp_path, build_signature="sig-1")
    cache.load()

    page_hash = cache.page_hash(
        raw_content="# Hello", metadata={"title": "Hello"}, layout="document"
    )
    # Nothing recorded yet -> treated as changed.
    assert cache.is_unchanged("out/index.html", page_hash) is False

    cache.record("out/index.html", page_hash)
    cache.save()

    # A fresh cache loading the saved manifest sees the page as unchanged.
    reloaded = BuildCache(tmp_path, build_signature="sig-1")
    reloaded.load()
    assert reloaded.is_unchanged("out/index.html", page_hash) is True


def test_changed_content_invalidates_entry(tmp_path: Path):
    cache = BuildCache(tmp_path, build_signature="sig-1")
    cache.record(
        "out/index.html",
        cache.page_hash(raw_content="v1", metadata={}, layout="document"),
    )
    cache.save()

    reloaded = BuildCache(tmp_path, build_signature="sig-1")
    reloaded.load()
    new_hash = reloaded.page_hash(raw_content="v2", metadata={}, layout="document")
    assert reloaded.is_unchanged("out/index.html", new_hash) is False


def test_build_signature_change_invalidates_whole_cache(tmp_path: Path):
    cache = BuildCache(tmp_path, build_signature="sig-1")
    page_hash = cache.page_hash(raw_content="v1", metadata={}, layout="document")
    cache.record("out/index.html", page_hash)
    cache.save()

    # A different signature (e.g. theme tokens changed) discards prior entries.
    reloaded = BuildCache(tmp_path, build_signature="sig-2")
    reloaded.load()
    assert reloaded.is_unchanged("out/index.html", page_hash) is False


def test_build_signature_is_stable_and_sensitive():
    base = {"theme_tokens": {"colors": {"accent": "#fff"}}, "plugins": ["A"]}
    changed = {"theme_tokens": {"colors": {"accent": "#000"}}, "plugins": ["A"]}
    assert compute_build_signature(base) == compute_build_signature(dict(base))
    assert compute_build_signature(base) != compute_build_signature(changed)
