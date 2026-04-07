import json
import os
import sys
from pathlib import Path
import tempfile
from unittest.mock import Mock

import pytest

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from cli import cmd_init  # noqa: E402
from core.config import Config  # noqa: E402
from core.extension_manager import ExtensionManager  # noqa: E402
from core.project import Project  # noqa: E402
from utils.fs_manager import FileSystemManager  # noqa: E402


def _write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _supports_python_dir_creation() -> bool:
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            (Path(temp_dir) / "probe").mkdir(parents=True, exist_ok=True)
        return True
    except PermissionError:
        return False


def test_v2_config_loads_platform_sections_and_synthesizes_react_target():
    mock_fs = Mock()
    mock_fs.read_file.return_value = """
version: 2
content:
  collections:
    shop:
      path: ./source/shop
      type: product
experimental:
  react:
    enabled: true
    collection: shop
    app_dir: ./react-app
"""

    config = Config(fs_manager=mock_fs)
    config.load(Path("config.yaml"))

    assert config.get("content.collections.shop.model") == "product"
    frontend_targets = config.get("frontend.targets")
    assert frontend_targets[0]["type"] == "spa_subtree"
    assert frontend_targets[0]["collection"] == "shop"


def test_extension_manager_loads_builtin_commerce_extension():
    config = Config()
    config.settings["extensions"]["enabled"] = ["wg-commerce"]

    manager = ExtensionManager(config, FileSystemManager())
    manager.detect_and_load_extensions()

    assert manager.model_registry.get("product") is not None
    assert manager.runtime_adapter_registry.describe(
        "commerce.payment.ir.shaparak_like"
    )["checkout_flow"] == "redirect_with_callback"
    assert any("wg_commerce" in template_dir for template_dir in manager.get_template_dirs())


def test_project_build_outputs_platform_artifacts():
    if not _supports_python_dir_creation():
        pytest.skip("Current interpreter cannot create directories in this environment.")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        shop_dir = temp_path / "shop"
        pages_dir = temp_path / "pages"
        site_theme_dir = temp_path / "site-theme"
        site_theme_dir.mkdir(parents=True, exist_ok=True)

        _write_markdown(
            shop_dir / "sample-product.md",
            """---
title: Sample Product
sku: SKU-001
price: 490000
currency: IRR
type: product
layout: product
highlights:
  - First-class commerce layout
variants:
  - id: default
    label: Default option
    price: 490000
blocks:
  - type: rich_text
    content:
      title: Sample
      html: |
        <p>Sample product body.</p>
---

# Sample Product
""",
        )
        _write_markdown(
            pages_dir / "home.md",
            """---
title: Home
type: index
layout: document
---

# Home
""",
        )

        output_dir = temp_path / "output"
        data_dir = output_dir / "data"

        config = Config()
        config.settings["site"]["navigation"] = []
        config.settings["build"]["output_directory"] = str(output_dir)
        config.settings["theme"]["site_theme_dir"] = str(site_theme_dir)
        config.settings["extensions"]["enabled"] = ["wg-commerce"]
        config.settings["frontend"]["targets"] = [
            {
                "type": "static_islands_bundle",
                "name": "store-ui",
                "mount_base": "/assets/frontend",
            }
        ]
        config.settings["frontend"]["islands"] = [
            {"name": "checkout_button", "component": "commerce/checkout_button"}
        ]
        config.settings["runtime"]["targets"] = [
            {
                "name": "commerce-api",
                "type": "fastapi_service",
                "public_base_url": "https://api.example.com",
                "capabilities": ["checkout", "payment_callback", "order_status"],
            }
        ]
        config.settings["integrations"] = {
            "payments": {
                "default": "iran_gateway",
                "providers": {
                    "iran_gateway": {
                        "adapter": "commerce.payment.ir.shaparak_like",
                        "runtime_target": "commerce-api",
                        "currency": "IRR",
                        "callback_url": "https://api.example.com/payments/callback",
                    }
                },
            }
        }
        config.settings["experimental"]["export_data"]["enabled"] = True
        config.settings["experimental"]["export_data"]["output_dir"] = str(data_dir)
        config.settings["content"]["collections"] = {
            "shop": {
                "path": str(shop_dir),
                "type": "product",
                "model": "product",
                "route": {"prefix": "shop"},
                "layout": "document",
            },
            "pages": {
                "path": str(pages_dir),
                "type": "page",
                "model": "page",
                "route": {"prefix": ""},
                "layout": "document",
            },
        }

        project = Project(config)
        project.build()

        html_path = output_dir / "shop" / "sample-product" / "index.html"
        runtime_manifest_path = output_dir / "runtime" / "manifest.json"
        frontend_script_path = output_dir / "assets" / "frontend" / "wg-islands.js"
        page_json_path = data_dir / "shop" / "sample-product" / "page.json"

        assert html_path.exists()
        assert runtime_manifest_path.exists()
        assert frontend_script_path.exists()
        assert page_json_path.exists()

        html = html_path.read_text(encoding="utf-8")
        assert 'data-wg-component="commerce/checkout_button"' in html
        assert 'id="purchase-panel"' in html

        page_payload = json.loads(page_json_path.read_text(encoding="utf-8"))
        assert page_payload["model"] == "product"
        assert page_payload["model_data"]["currency"] == "IRR"
        assert page_payload["model_data"]["price"] == 490000.0

        runtime_manifest = json.loads(runtime_manifest_path.read_text(encoding="utf-8"))
        provider_cfg = runtime_manifest["integrations"]["payments"]["providers"]["iran_gateway"]
        assert provider_cfg["adapter"] == "commerce.payment.ir.shaparak_like"
        assert provider_cfg["adapter_metadata"]["kind"] == "payment_provider"


def test_init_store_ir_payments_scaffolds_platform_project():
    if not _supports_python_dir_creation():
        pytest.skip("Current interpreter cannot create directories in this environment.")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        target = temp_path / "store"

        cmd_init(
            type(
                "Args",
                (),
                {"directory": str(target), "starter": "store-ir-payments"},
            )()
        )

        config_text = (target / "config.yaml").read_text(encoding="utf-8")
        assert "commerce.payment.ir.shaparak_like" in config_text
        assert "store-ui" in config_text
        assert (target / "source" / "shop" / "sample-product.md").exists()
        assert (target / "source" / "pages" / "order-status.md").exists()
