from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from utils.fs_manager import FileSystemManager


STARTER_NAMES = [
    "blog",
    "docs",
    "portfolio",
    "store",
    "store-ir-payments",
]


THEME_SETTINGS = dedent(
    """\
    preset: default
    presets:
      header: default
      footer: default
      cards: default
      blog_index: default
      post: default
      buttons: default
    tokens:
      colors:
        bg: "#f8fafc"
        surface: "#ffffff"
        text: "#0f172a"
        muted: "#475569"
        accent: "#0f766e"
        border: "#dbe4ee"
      typography:
        body-family: "'Segoe UI', sans-serif"
        heading-family: "'Georgia', serif"
    stylesheets: []
    scripts: []
    """
)


def scaffold_starter(target_dir: Path, starter: str, fs_manager: FileSystemManager) -> None:
    if starter not in STARTER_NAMES:
        raise ValueError(f"Unknown starter: {starter}")

    for relative_dir in [
        "source",
        "source/assets",
        "source/data",
        "site-theme",
        "styles",
    ]:
        fs_manager.create_directory(target_dir / relative_dir)

    starter_files = _build_starter_files(starter)
    for relative_path, content in starter_files.items():
        fs_manager.write_file(target_dir / relative_path, content)


def _build_starter_files(starter: str) -> dict[Path, str]:
    builders = {
        "blog": _blog_files,
        "docs": _docs_files,
        "portfolio": _portfolio_files,
        "store": _store_files,
        "store-ir-payments": _store_ir_files,
    }
    return builders[starter]()


def _common_files(config: str) -> dict[Path, str]:
    return {
        Path("config.yaml"): dedent(config).strip() + "\n",
        Path("theme.settings.yaml"): THEME_SETTINGS,
    }


def _blog_files() -> dict[Path, str]:
    files = _common_files(
        """
        version: 2
        site:
          name: My Site
          description: A new site powered by wg.
          base_url: http://localhost:8000
          author: Your Name
          navigation:
            - title: Home
              type: index
            - title: Blog
              collection_index: blog
        content:
          source_directory: ./source
          data_dir: ./source/data
          collections:
            blog:
              path: ./source/blogs
              type: blog
              model: post
              route:
                prefix: blog
              layout: document
              index:
                enabled: true
                layout: collection
                title: Blog
            pages:
              path: ./source
              type: page
              model: page
              route:
                prefix: ""
              layout: document
        build:
          output_directory: ./output
          asset_dirs:
            - ./source/assets
          template_engine: django
          log_level: 20
        theme:
          name: minimal-blog
          settings: ./theme.settings.yaml
          site_theme_dir: ./site-theme
        extensions:
          enabled: []
        frontend:
          targets: []
          islands: []
        runtime:
          targets: []
        integrations: {}
        plugins:
          - CollectionIndexerPlugin
          - SpecialPagesPlugin
          - PageKeyWordExtractor
          - SitemapPlugin
        experimental:
          export_data:
            enabled: false
            output_dir: ./output/data
            include_collections: []
          react:
            enabled: false
            collection: ""
            app_dir: ./react-app
            export_subdir: ""
            base_path: ""
            asset_prefix: ""
          tailwind:
            enabled: false
            input: ./styles/tailwind.input.css
            output: ./styles/tailwind.css
            config: ./tailwind.config.js
            minify: false
        """
    )
    files[Path("source/index.md")] = dedent(
        """\
        ---
        title: Home
        type: index
        layout: document
        ---

        # Welcome

        This is your new static-first site.
        """
    )
    files[Path("source/blogs/hello-world.md")] = dedent(
        """\
        ---
        title: Hello World
        summary: Your first generated post.
        date: 2026-04-04
        type: blog
        layout: document
        ---

        # Hello World

        Start building.
        """
    )
    return files


def _docs_files() -> dict[Path, str]:
    files = _common_files(
        """
        version: 2
        site:
          name: Docs Site
          description: Documentation starter.
          base_url: http://localhost:8000
          navigation:
            - title: Home
              type: index
            - title: Docs
              collection_index: docs
        content:
          source_directory: ./source
          data_dir: ./source/data
          collections:
            docs:
              path: ./source/docs
              type: doc
              model: doc
              route:
                prefix: docs
              layout: document
              index:
                enabled: true
                layout: collection
                title: Docs
            pages:
              path: ./source
              type: page
              model: page
              route:
                prefix: ""
              layout: document
        build:
          output_directory: ./output
          asset_dirs:
            - ./source/assets
          template_engine: django
          log_level: 20
        theme:
          name: docs-basic
          settings: ./theme.settings.yaml
          site_theme_dir: ./site-theme
        extensions:
          enabled: []
        frontend:
          targets: []
          islands: []
        runtime:
          targets: []
        integrations: {}
        plugins:
          - CollectionIndexerPlugin
          - SpecialPagesPlugin
          - SitemapPlugin
        experimental:
          export_data:
            enabled: false
            output_dir: ./output/data
            include_collections: []
          react:
            enabled: false
            collection: ""
            app_dir: ./react-app
            export_subdir: ""
            base_path: ""
            asset_prefix: ""
          tailwind:
            enabled: false
            input: ./styles/tailwind.input.css
            output: ./styles/tailwind.css
            config: ./tailwind.config.js
            minify: false
        """
    )
    files[Path("source/index.md")] = "---\ntitle: Home\ntype: index\nlayout: document\n---\n\n# Docs\n\nStart documenting.\n"
    files[Path("source/docs/getting-started.md")] = "---\ntitle: Getting Started\nsummary: First docs page.\ntype: doc\nlayout: document\n---\n\n# Getting Started\n\nWrite docs here.\n"
    return files


def _portfolio_files() -> dict[Path, str]:
    files = _common_files(
        """
        version: 2
        site:
          name: Portfolio
          description: Portfolio starter.
          base_url: http://localhost:8000
          navigation:
            - title: Home
              type: index
        content:
          source_directory: ./source
          data_dir: ./source/data
          collections:
            pages:
              path: ./source
              type: landing
              model: landing
              route:
                prefix: ""
              layout: document
        build:
          output_directory: ./output
          asset_dirs:
            - ./source/assets
          template_engine: django
          log_level: 20
        theme:
          name: editorial-ledger
          settings: ./theme.settings.yaml
          site_theme_dir: ./site-theme
        extensions:
          enabled: []
        frontend:
          targets: []
          islands: []
        runtime:
          targets: []
        integrations: {}
        plugins:
          - SpecialPagesPlugin
          - SitemapPlugin
        experimental:
          export_data:
            enabled: false
            output_dir: ./output/data
            include_collections: []
          react:
            enabled: false
            collection: ""
            app_dir: ./react-app
            export_subdir: ""
            base_path: ""
            asset_prefix: ""
          tailwind:
            enabled: false
            input: ./styles/tailwind.input.css
            output: ./styles/tailwind.css
            config: ./tailwind.config.js
            minify: false
        """
    )
    files[Path("source/index.md")] = dedent(
        """\
        ---
        title: Home
        type: index
        layout: document
        blocks:
          - type: hero
            content:
              eyebrow: Portfolio
              title: A bold starting point
              text: Tell your story with blocks and Markdown.
        ---

        # Portfolio

        Add projects, services, and case studies.
        """
    )
    return files


def _store_base_files() -> dict[Path, str]:
    files = _common_files(
        """
        version: 2
        site:
          name: Storefront
          description: Static-first commerce starter.
          base_url: http://localhost:8000
          navigation:
            - title: Home
              type: index
            - title: Shop
              collection_index: shop
            - title: Order Status
              type: order-status
        content:
          source_directory: ./source
          data_dir: ./source/data
          collections:
            shop:
              path: ./source/shop
              type: product
              model: product
              route:
                prefix: shop
              layout: document
              index:
                enabled: true
                layout: collection
                title: Shop
            pages:
              path: ./source/pages
              type: page
              model: page
              route:
                prefix: ""
              layout: document
        build:
          output_directory: ./output
          asset_dirs:
            - ./source/assets
          template_engine: django
          log_level: 20
        theme:
          name: minimal-blog
          settings: ./theme.settings.yaml
          site_theme_dir: ./site-theme
        extensions:
          enabled:
            - wg-commerce
            - wg-seo
            - wg-sitemap
        frontend:
          targets:
            - type: static_islands_bundle
              name: store-ui
              mount_base: /assets/frontend
          islands:
            - name: cart
              component: commerce/cart
            - name: checkout_button
              component: commerce/checkout_button
            - name: order_status
              component: commerce/order_status
        runtime:
          targets:
            - name: commerce-api
              type: django_service
              public_base_url: https://api.example.com
              capabilities:
                - checkout
                - payment_callback
                - order_status
          catalog_snapshot:
            enabled: false
            target: commerce-api
            url_path: /catalog/snapshot
            output_dir: ./output/data/runtime
        integrations:
          commerce:
            provider: wg-commerce
        plugins:
          - CollectionIndexerPlugin
          - SpecialPagesPlugin
          - PageKeyWordExtractor
          - SitemapPlugin
        experimental:
          export_data:
            enabled: true
            output_dir: ./output/data
            include_collections: []
          react:
            enabled: false
            collection: ""
            app_dir: ./react-app
            export_subdir: ""
            base_path: ""
            asset_prefix: ""
          tailwind:
            enabled: false
            input: ./styles/tailwind.input.css
            output: ./styles/tailwind.css
            config: ./tailwind.config.js
            minify: false
        """
    )
    files[Path("source/pages/index.md")] = dedent(
        """\
        ---
        title: Home
        type: index
        layout: document
        blocks:
          - type: commerce/cart
            content:
              title: Cart
              text: Your storefront can stay static while this island mounts interactive cart UI.
        ---

        # Storefront

        Browse products and start checkout through runtime adapters.
        """
    )
    files[Path("source/pages/order-status.md")] = dedent(
        """\
        ---
        title: Order Status
        type: order-status
        layout: document
        blocks:
          - type: commerce/order_status
            content:
              title: Check your order
              text: Runtime APIs can expose public order state here.
        ---

        # Order Status
        """
    )
    files[Path("source/shop/sample-product.md")] = dedent(
        """\
        ---
        title: Sample Product
        summary: Static product page with runtime checkout.
        sku: SKU-001
        price: 490000
        currency: IRR
        availability: in_stock
        payment_methods:
          - iran_gateway
        checkout_provider: iran_gateway
        type: product
        layout: document
        blocks:
          - type: commerce/checkout_button
            content:
              label: Buy now
            settings:
              runtime_target: commerce-api
        ---

        # Sample Product

        This page is static. Checkout is not.
        """
    )
    return files


def _store_files() -> dict[Path, str]:
    return _store_base_files()


def _store_ir_files() -> dict[Path, str]:
    files = _store_base_files()
    files[Path("config.yaml")] = files[Path("config.yaml")].replace(
        "integrations:\n  commerce:\n    provider: wg-commerce\n",
        dedent(
            """\
            integrations:
              commerce:
                provider: wg-commerce
              payments:
                default: iran_gateway
                providers:
                  iran_gateway:
                    adapter: commerce.payment.ir.shaparak_like
                    runtime_target: commerce-api
                    currency: IRR
                    callback_url: https://api.example.com/payments/callback
            """
        ),
    )
    return files
