"""Page rendering: context assembly, template resolution, and HTML output.

Extracted from the former ``Project`` god class. The page context is now built
exactly once per page (the previous implementation built the full context dict
twice - once to render blocks and once for the final render); blocks are
rendered against that single context and then attached to it.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .build_context import BuildContext
from .errors import BuildError
from .page import Page


class PageContextBuilder:
    """Assembles the template context for a single page."""

    def __init__(self, ctx: BuildContext) -> None:
        self.ctx = ctx

    def build(self, page: Page, header: str, navigation_items: list[dict]) -> dict:
        ctx = self.ctx
        stylesheets = ctx.theme_manager.get_stylesheets()
        scripts = ctx.theme_manager.get_scripts()
        layout_options = ctx.theme_manager.get_layout_options(page)
        theme_context = ctx.theme_manager.get_theme_context()

        self._collect_injected_assets(page, "inject_css", stylesheets)
        self._collect_injected_assets(page, "inject_js", scripts)

        frontend_context = ctx.frontend_manager.get_context()
        runtime_context = ctx.runtime_manager.get_context()
        extensions_context = ctx.extension_manager.get_context()
        bootstrap_script = frontend_context.get("frontend", {}).get("bootstrap_script", "")
        if bootstrap_script and bootstrap_script not in scripts:
            scripts.append(bootstrap_script)

        context = page.get_context(
            header=header,
            site=ctx.site,
            stylesheets=stylesheets,
            scripts=scripts,
            navigation_items=navigation_items,
            theme_context=theme_context,
            layout_options=layout_options,
            frontend_context=frontend_context,
            runtime_context=runtime_context,
            extensions_context=extensions_context,
        )

        # Render blocks against the single context, then attach the result.
        context["rendered_blocks"] = ctx.theme_manager.render_blocks(
            page.blocks, ctx.template_engine, context
        )

        self._apply_context_plugins(page, context)
        return context

    def _collect_injected_assets(self, page: Page, hook: str, sink: list[str]) -> None:
        ctx = self.ctx
        for injected in ctx.plugin_manager.run_hook_collect(
            hook,
            site=ctx.site,
            config=ctx.config,
            fs_manager=ctx.fs_manager,
            page=page,
        ):
            if isinstance(injected, str):
                sink.append(injected)
            elif isinstance(injected, (list, tuple)):
                sink.extend(injected)

    def _apply_context_plugins(self, page: Page, context: dict) -> None:
        ctx = self.ctx
        for hook in ("modify_context", "modify_template_context"):
            for update in ctx.plugin_manager.run_hook_collect(
                hook,
                context=context,
                site=ctx.site,
                config=ctx.config,
                fs_manager=ctx.fs_manager,
                page=page,
            ):
                if isinstance(update, dict):
                    context.update(update)


class TemplateResolver:
    """Resolves which theme layout a page should render with."""

    def __init__(self, ctx: BuildContext) -> None:
        self.ctx = ctx

    def resolve(self, page: Page) -> str:
        requested_layout = page.layout
        if not requested_layout and isinstance(page.collection_config, dict):
            requested_layout = (
                page.collection_config.get("layout")
                or page.collection_config.get("defaults", {}).get("layout")
            )

        if page.is_not_found_page():
            requested_layout = "not_found"
        elif page.is_collection_index and not requested_layout:
            requested_layout = "collection"

        if not requested_layout:
            templates_by_type = self.ctx.config.get("content.templates_by_type", {})
            if isinstance(templates_by_type, dict):
                requested_layout = templates_by_type.get(page.page_type)

        if not requested_layout:
            requested_layout = "document"

        return self.ctx.theme_manager.resolve_layout(str(requested_layout), page)


class PageRenderer:
    """Renders every page in the site to HTML and writes it to disk."""

    def __init__(self, ctx: BuildContext) -> None:
        self.ctx = ctx
        self.logger = logging.getLogger(__name__)
        self.context_builder = PageContextBuilder(ctx)
        self.template_resolver = TemplateResolver(ctx)

    def render_all(self) -> None:
        ctx = self.ctx
        self.logger.info("Rendering pages...")
        navigation_items = ctx.site.build_navigation()
        header = ctx.site.populate_header()

        cache = ctx.build_cache if ctx.incremental else None
        if cache is not None:
            cache.load()

        for page in ctx.site.pages:
            output_path = page.get_output_path()
            if output_path is None:
                raise BuildError(f"No output path assigned for page '{page.title}'")

            if cache is not None and self._skip_unchanged(page, output_path, cache):
                self.logger.debug("Skipping unchanged page: %s", page.source_filepath)
                continue

            ctx.plugin_manager.run_hook(
                "before_page_rendered",
                site=ctx.site,
                config=ctx.config,
                fs_manager=ctx.fs_manager,
                page=page,
            )

            context = self.context_builder.build(page, header, navigation_items)
            template_name = self.template_resolver.resolve(page)
            rendered_html = ctx.template_engine.render(template_name, context)

            ctx.fs_manager.write_file(output_path, rendered_html)
            self.logger.debug(
                "Rendered page: %s -> %s", page.source_filepath, output_path
            )

            ctx.plugin_manager.run_hook(
                "after_page_rendered",
                site=ctx.site,
                config=ctx.config,
                fs_manager=ctx.fs_manager,
                page=page,
            )

        if cache is not None:
            cache.save()

    def _skip_unchanged(self, page, output_path, cache) -> bool:
        """Return True (and record the hash) when a page can be reused as-is."""
        key = str(output_path)
        page_hash = cache.page_hash(
            raw_content=page.raw_content,
            metadata=page.metadata,
            layout=page.layout,
        )
        cache.record(key, page_hash)
        return cache.is_unchanged(key, page_hash) and output_path.exists()
