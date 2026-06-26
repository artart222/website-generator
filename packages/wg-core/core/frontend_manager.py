from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from utils.fs_manager import FileSystemManager


FrontendTargetBuilder = Callable[..., dict[str, Any]]


def build_static_islands_bundle(
    *,
    target: dict[str, Any],
    config,
    fs_manager: FileSystemManager,
    output_dir: Path,
    logger: logging.Logger,
    runtime_public_config: dict[str, Any],
) -> dict[str, Any]:
    mount_base = str(target.get("mount_base", "/assets/frontend")).rstrip("/")
    asset_dir = output_dir / mount_base.lstrip("/")
    fs_manager.create_directory(asset_dir)

    target_name = str(target.get("name", "frontend"))
    manifest_filename = str(target.get("manifest_filename", f"{target_name}.manifest.json"))
    manifest_path = asset_dir / manifest_filename

    frontend_cfg = config.get("frontend", {})
    islands = frontend_cfg.get("islands", []) if isinstance(frontend_cfg, dict) else []
    manifest = {
        "target": target_name,
        "type": "static_islands_bundle",
        "mount_base": mount_base,
        "islands": islands if isinstance(islands, list) else [],
        "runtime": runtime_public_config,
    }
    fs_manager.write_file(
        manifest_path,
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
    )

    bootstrap_js_path = asset_dir / "wg-islands.js"
    bootstrap_script = """(function () {
  var runtimeConfigPromise = null;

  function toProps(element) {
    var props = {};
    Object.keys(element.dataset).forEach(function (key) {
      if (!key.startsWith('wg')) {
        props[key] = element.dataset[key];
      }
    });
    return props;
  }

  function resolveUrl(path) {
    if (!path) {
      return '';
    }
    if (/^https?:\\/\\//i.test(path)) {
      return path;
    }
    return new URL(path, window.location.origin).toString();
  }

  function formatPrice(value) {
    var number = Number(value || 0);
    if (!Number.isFinite(number)) {
      return String(value || '');
    }
    return new Intl.NumberFormat('en-US', {
      maximumFractionDigits: 0
    }).format(number);
  }

  function getRuntimeConfig() {
    if (!runtimeConfigPromise) {
      runtimeConfigPromise = fetch('/runtime/public-config.json', {
        credentials: 'same-origin'
      }).then(function (response) {
        if (!response.ok) {
          throw new Error('Unable to load runtime config');
        }
        return response.json();
      }).catch(function () {
        return { targets: [], integrations: {} };
      });
    }
    return runtimeConfigPromise;
  }

  function findRuntimeTarget(config, targetName) {
    var targets = Array.isArray(config.targets) ? config.targets : [];
    if (targetName) {
      for (var index = 0; index < targets.length; index += 1) {
        if (targets[index] && targets[index].name === targetName) {
          return targets[index];
        }
      }
    }
    return targets.length ? targets[0] : null;
  }

  function setCheckoutFeedback(element, text, isError) {
    var feedback = element.querySelector('[data-checkout-feedback]');
    if (!feedback) {
      return;
    }
    feedback.textContent = text || '';
    feedback.style.color = isError ? '#8d1f1f' : '';
  }

  function readQuantity(element) {
    var selector = element.dataset.wgQuantitySelector;
    var input = selector ? document.querySelector(selector) : null;
    var value = input ? Number(input.value || 1) : 1;
    if (!Number.isFinite(value) || value < 1) {
      return 1;
    }
    return Math.round(value);
  }

  function readVariant(element) {
    var selector = element.dataset.wgVariantSelector;
    var input = selector ? document.querySelector(selector) : null;
    if (!input || !input.selectedOptions || !input.selectedOptions.length) {
      return null;
    }
    var option = input.selectedOptions[0];
    return {
      id: option.value || '',
      label: option.dataset.label || option.textContent || '',
      note: option.dataset.note || '',
      price: option.dataset.price || element.dataset.wgPrice || ''
    };
  }

  function readCart() {
    try {
      var raw = window.localStorage.getItem('wg-cart');
      if (!raw) {
        return { items: [] };
      }
      var parsed = JSON.parse(raw);
      if (!parsed || !Array.isArray(parsed.items)) {
        return { items: [] };
      }
      return parsed;
    } catch (error) {
      return { items: [] };
    }
  }

  function writeCart(cart) {
    try {
      window.localStorage.setItem('wg-cart', JSON.stringify(cart));
    } catch (error) {
      /* ignore localStorage failures */
    }
  }

  function renderCart(element) {
    var list = element.querySelector('[data-cart-list]');
    if (!list) {
      return;
    }
    var cart = readCart();
    list.innerHTML = '';
    if (!cart.items.length) {
      var emptyItem = document.createElement('li');
      emptyItem.className = 'wg-commerce-cart__item';
      emptyItem.textContent = 'Your cart is empty. Product selections will appear here.';
      list.appendChild(emptyItem);
      return;
    }
    cart.items.forEach(function (item) {
      var row = document.createElement('li');
      row.className = 'wg-commerce-cart__item';
      row.textContent = item.title + ' x' + item.quantity + ' - ' + item.currency + ' ' + formatPrice(item.price);
      list.appendChild(row);
    });
  }

  function syncCartFromSelection(element) {
    var variant = readVariant(element);
    var quantity = readQuantity(element);
    var cart = {
      items: [{
        sku: element.dataset.wgSku || '',
        title: element.dataset.wgProductTitle || 'Product',
        price: variant && variant.price ? variant.price : element.dataset.wgPrice || '',
        currency: element.dataset.wgCurrency || 'IRR',
        quantity: quantity,
        variantId: variant ? variant.id : '',
        variantLabel: variant ? variant.label : ''
      }]
    };
    writeCart(cart);
    document.querySelectorAll('[data-wg-component=\"commerce/cart\"]').forEach(renderCart);
  }

  function mountProductGallery() {
    document.querySelectorAll('[data-product-gallery]').forEach(function (gallery) {
      if (gallery.dataset.galleryMounted === 'true') {
        return;
      }
      var mainImage = gallery.querySelector('[data-product-main-image]');
      if (!mainImage) {
        gallery.dataset.galleryMounted = 'true';
        return;
      }
      gallery.querySelectorAll('[data-product-thumb]').forEach(function (thumb) {
        thumb.addEventListener('click', function () {
          if (mainImage.tagName === 'IMG') {
            mainImage.src = thumb.dataset.imageSrc || mainImage.src;
            mainImage.alt = thumb.dataset.imageAlt || mainImage.alt;
          }
          gallery.querySelectorAll('[data-product-thumb]').forEach(function (item) {
            item.classList.remove('is-active');
          });
          thumb.classList.add('is-active');
        });
      });
      gallery.dataset.galleryMounted = 'true';
    });
  }

  function mountProductPanel(element) {
    if (element.dataset.panelMounted === 'true') {
      return;
    }
    var selector = element.dataset.wgVariantSelector ? document.querySelector(element.dataset.wgVariantSelector) : null;
    var priceNode = document.querySelector('[data-product-price]');
    var noteNode = document.querySelector('[data-product-variant-note]');

    function syncVariant() {
      var variant = readVariant(element);
      if (variant && variant.price) {
        element.dataset.wgPrice = variant.price;
        if (priceNode) {
          priceNode.textContent = formatPrice(variant.price);
        }
      } else if (priceNode) {
        priceNode.textContent = formatPrice(element.dataset.wgPrice || '');
      }
      if (noteNode && variant) {
        noteNode.textContent = variant.note || '';
      }
    }

    if (selector) {
      selector.addEventListener('change', syncVariant);
    }
    syncVariant();
    element.dataset.panelMounted = 'true';
  }

  function mountCheckoutButton(element) {
    if (element.dataset.wgCheckoutMounted === 'true') {
      return;
    }
    var button = element.querySelector('button');
    if (!button) {
      return;
    }

    mountProductPanel(element);

    button.addEventListener('click', function () {
      button.disabled = true;
      setCheckoutFeedback(element, 'Creating checkout session...', false);
      syncCartFromSelection(element);

      var variant = readVariant(element);
      var lineItem = {
        sku: element.dataset.wgSku || '',
        title: element.dataset.wgProductTitle || '',
        price: variant && variant.price ? variant.price : element.dataset.wgPrice || '',
        currency: element.dataset.wgCurrency || 'IRR',
        quantity: readQuantity(element),
        variant_id: variant ? variant.id : '',
        variant_label: variant ? variant.label : ''
      };

      var payload = {
        currency: element.dataset.wgCurrency || 'IRR',
        success_url: resolveUrl(element.dataset.wgSuccessUrl || '/order-confirmed/'),
        failure_url: resolveUrl(element.dataset.wgFailureUrl || '/payment-not-completed/'),
        status_url: resolveUrl(element.dataset.wgStatusUrl || '/order-status/'),
        lines: [lineItem]
      };

      getRuntimeConfig().then(function (runtimeConfig) {
        var target = findRuntimeTarget(runtimeConfig, element.dataset.wgRuntimeTarget || '');
        if (!target || !target.public_base_url) {
          throw new Error('Runtime target is not configured');
        }
        return fetch(target.public_base_url.replace(/\\/$/, '') + '/checkout/session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(payload)
        });
      }).then(function (response) {
        if (!response.ok) {
          throw new Error('Checkout request failed');
        }
        return response.json();
      }).then(function (payload) {
        if (payload && payload.order_id) {
          try {
            window.localStorage.setItem('wg-last-order-id', payload.order_id);
          } catch (error) {
            /* ignore localStorage failures */
          }
        }
        if (payload && payload.redirect_url) {
          window.location.href = payload.redirect_url;
          return;
        }
        throw new Error('Checkout response missing redirect_url');
      }).catch(function (error) {
        setCheckoutFeedback(element, error.message || 'Checkout failed', true);
        button.disabled = false;
      });
    });

    element.dataset.wgCheckoutMounted = 'true';
  }

  function renderOrderStatus(element, payload) {
    var result = element.querySelector('[data-order-status-result]');
    if (!result) {
      return;
    }
    if (!payload) {
      result.textContent = 'Order not found.';
      return;
    }
    var summary = payload.order_id + ' - ' + payload.status;
    if (payload.variant_label) {
      summary += ' - ' + payload.variant_label;
    }
    if (payload.reference) {
      summary += ' - ref ' + payload.reference;
    }
    result.textContent = summary;
  }

  function mountOrderStatus(element) {
    if (element.dataset.statusMounted === 'true') {
      return;
    }
    var form = element.querySelector('[data-order-status-form]');
    var input = element.querySelector('[data-order-status-input]');
    if (!form || !input) {
      return;
    }

    function lookup(orderId) {
      if (!orderId) {
        renderOrderStatus(element, null);
        return Promise.resolve();
      }
      return getRuntimeConfig().then(function (runtimeConfig) {
        var target = findRuntimeTarget(runtimeConfig, element.dataset.wgRuntimeTarget || '');
        if (!target || !target.public_base_url) {
          throw new Error('Runtime target is not configured');
        }
        return fetch(target.public_base_url.replace(/\\/$/, '') + '/orders/' + encodeURIComponent(orderId), {
          method: 'GET'
        });
      }).then(function (response) {
        if (!response.ok) {
          throw new Error('Order status lookup failed');
        }
        return response.json();
      }).then(function (payload) {
        renderOrderStatus(element, payload);
      }).catch(function (error) {
        var result = element.querySelector('[data-order-status-result]');
        if (result) {
          result.textContent = error.message || 'Order status lookup failed.';
        }
      });
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      lookup(input.value.trim());
    });

    var params = new URLSearchParams(window.location.search);
    var presetOrderId = params.get('order_id') || '';
    if (!presetOrderId) {
      try {
        presetOrderId = window.localStorage.getItem('wg-last-order-id') || '';
      } catch (error) {
        presetOrderId = '';
      }
    }
    if (presetOrderId) {
      input.value = presetOrderId;
      lookup(presetOrderId);
    }

    element.dataset.statusMounted = 'true';
  }

  function mountCart(element) {
    if (element.dataset.cartMounted === 'true') {
      return;
    }
    renderCart(element);
    element.dataset.cartMounted = 'true';
  }

  function mountIsland(element) {
    if (element.dataset.wgIslandMounted === 'true') {
      return;
    }
    var detail = {
      component: element.dataset.wgComponent || '',
      target: element.dataset.wgTarget || '',
      props: toProps(element)
    };
    element.dataset.wgIslandMounted = 'true';
    if (detail.component === 'commerce/checkout_button') {
      mountCheckoutButton(element);
    } else if (detail.component === 'commerce/order_status') {
      mountOrderStatus(element);
    } else if (detail.component === 'commerce/cart') {
      mountCart(element);
    }
    element.dispatchEvent(new CustomEvent('wg:island-mount', {
      bubbles: true,
      detail: detail
    }));
  }

  document.addEventListener('DOMContentLoaded', function () {
    mountProductGallery();
    document.querySelectorAll('[data-wg-island]').forEach(mountIsland);
  });
})();"""
    fs_manager.write_file(bootstrap_js_path, bootstrap_script)

    return {
        "name": target_name,
        "type": "static_islands_bundle",
        "mount_base": mount_base,
        "manifest_path": f"{mount_base}/{manifest_filename}",
        "bootstrap_script": f"{mount_base}/wg-islands.js",
    }


def build_spa_subtree(
    *,
    target: dict[str, Any],
    config,
    fs_manager: FileSystemManager,
    output_dir: Path,
    logger: logging.Logger,
    runtime_public_config: dict[str, Any],
) -> dict[str, Any]:
    framework = str(target.get("framework", "next_static_export"))
    app_dir = Path(target.get("app_dir", "./react-app"))
    export_subdir = str(target.get("export_subdir") or target.get("name") or "app").strip("/\\")
    dest_dir = output_dir / export_subdir

    export_data = config.get("experimental.export_data", {})
    if not isinstance(export_data, dict):
        export_data = {}
    data_dir = Path(export_data.get("output_dir", "./output/data"))

    if framework == "next_static_export":
        if not app_dir.exists():
            raise FileNotFoundError(f"Frontend app directory not found: {app_dir}")

        public_data_dir = app_dir / "public" / "data"
        if data_dir.exists():
            if public_data_dir.exists():
                shutil.rmtree(public_data_dir)
            fs_manager.copy_directory(data_dir, public_data_dir, exist_ok=True)

        if not target.get("skip_build", False):
            npm = shutil.which("npm")
            if npm is None:
                raise RuntimeError("npm not found. Please install Node.js.")

            env = os.environ.copy()
            env["NEXT_PUBLIC_BASE_PATH"] = str(target.get("base_path", f"/{export_subdir}"))
            env["NEXT_PUBLIC_ASSET_PREFIX"] = str(
                target.get("asset_prefix", target.get("base_path", f"/{export_subdir}"))
            )
            env["NEXT_PUBLIC_COLLECTION"] = str(target.get("collection", ""))
            env["NEXT_PUBLIC_DATA_URL"] = str(target.get("data_url", "/data"))
            env["NEXT_PUBLIC_RUNTIME_CONFIG"] = json.dumps(runtime_public_config)
            subprocess.run([npm, "run", "build"], cwd=str(app_dir), env=env, check=True)

        export_dir = app_dir / "out"
        if not export_dir.exists():
            raise FileNotFoundError(f"Frontend export directory not found: {export_dir}")
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        fs_manager.copy_directory(export_dir, dest_dir, exist_ok=True)

    return {
        "name": str(target.get("name", export_subdir)),
        "type": "spa_subtree",
        "framework": framework,
        "output_subdir": export_subdir,
    }


def build_custom_framework_target(
    *,
    target: dict[str, Any],
    config,
    fs_manager: FileSystemManager,
    output_dir: Path,
    logger: logging.Logger,
    runtime_public_config: dict[str, Any],
) -> dict[str, Any]:
    target_name = str(target.get("name", "custom-framework"))
    source_dir = Path(target.get("source_dir", ""))
    export_subdir = str(target.get("export_subdir", target_name)).strip("/\\")
    dest_dir = output_dir / export_subdir

    if source_dir and source_dir.exists():
        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        fs_manager.copy_directory(source_dir, dest_dir, exist_ok=True)

    return {
        "name": target_name,
        "type": "custom_framework_target",
        "output_subdir": export_subdir,
    }


BUILTIN_TARGET_BUILDERS: dict[str, FrontendTargetBuilder] = {
    "static_islands_bundle": build_static_islands_bundle,
    "spa_subtree": build_spa_subtree,
    "custom_framework_target": build_custom_framework_target,
}


class FrontendManager:
    """Builds frontend targets and exposes frontend context to templates."""

    def __init__(self, config, fs_manager: FileSystemManager, extension_manager) -> None:
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.fs_manager = fs_manager
        self.extension_manager = extension_manager
        self.built_targets: list[dict[str, Any]] = []

    def build_targets(self, runtime_public_config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        frontend_cfg = self.config.get("frontend", {})
        if not isinstance(frontend_cfg, dict):
            frontend_cfg = {}

        targets = frontend_cfg.get("targets", [])
        if not isinstance(targets, list):
            targets = []

        output_dir = Path(
            self.config.get("build.output_directory", self.config.get("output_directory"))
        )
        runtime_public_config = runtime_public_config or {}
        self.built_targets = []

        for raw_target in targets:
            if not isinstance(raw_target, dict):
                continue

            target_type = str(raw_target.get("type", "")).strip()
            if not target_type:
                continue

            builder = self.extension_manager.frontend_target_registry.get(target_type)
            if builder is None:
                builder = BUILTIN_TARGET_BUILDERS.get(target_type)
            if builder is None:
                self.logger.warning("Unknown frontend target type: %s", target_type)
                continue

            result = builder(
                target=raw_target,
                config=self.config,
                fs_manager=self.fs_manager,
                output_dir=output_dir,
                logger=self.logger,
                runtime_public_config=runtime_public_config,
            )
            self.built_targets.append(result)

        return self.built_targets

    def get_context(self) -> dict[str, Any]:
        frontend_cfg = self.config.get("frontend", {})
        if not isinstance(frontend_cfg, dict):
            frontend_cfg = {}
        configured_targets = frontend_cfg.get("targets", [])
        if not isinstance(configured_targets, list):
            configured_targets = []
        static_target = next(
            (
                target
                for target in configured_targets
                if isinstance(target, dict) and target.get("type") == "static_islands_bundle"
            ),
            None,
        )
        has_static_bundle = any(
            isinstance(target, dict) and target.get("type") == "static_islands_bundle"
            for target in configured_targets
        ) or any(target.get("type") == "static_islands_bundle" for target in self.built_targets)
        bootstrap_script = "/assets/frontend/wg-islands.js"
        if isinstance(static_target, dict):
            bootstrap_script = str(static_target.get("mount_base", "/assets/frontend")).rstrip("/") + "/wg-islands.js"
        return {
            "frontend": {
                "targets": json.loads(json.dumps(self.built_targets or configured_targets)),
                "islands": json.loads(json.dumps(frontend_cfg.get("islands", [])))
                if isinstance(frontend_cfg.get("islands", []), list)
                else [],
                "bootstrap_script": bootstrap_script if has_static_bundle else "",
            }
        }
