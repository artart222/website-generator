---
title: Copper Tea Tray
summary: Hammered copper serving tray designed for tea, sweets, and late-night conversations.
description: Catalog-style product example with a stronger purchase panel, gallery assets, and runtime-backed payment configuration.
sku: COPPER-TRAY-01
price: 3290000
price_compare_at: 3560000
currency: IRR
availability: in_stock
badge: Ceremony piece
images:
  - /assets/products/copper-tea-tray-hero.svg
  - /assets/products/copper-tea-tray-detail.svg
  - /assets/products/copper-tea-tray-table.svg
variant_name: Diameter
variants:
  - id: tray-34
    label: 34 cm service tray
    price: 3290000
    note: Best fit for four to six glasses plus sweets or sugar cubes.
  - id: tray-38
    label: 38 cm hosting tray
    price: 3590000
    note: Adds room for a full host setup when tea, saffron, and sweets share one surface.
highlights:
  - Hammered finish catches light without feeling overly polished.
  - Sized for real serving rituals, not just shelf styling.
  - Pairs well with the ceramic tea set in this demo.
shipping_note: Ships in a rigid sleeve with edge guards to protect the hammered rim.
lead_time: Leaves the workshop in 3 business days.
payment_methods:
  - iran_gateway
checkout_provider: iran_gateway
attributes:
  Finish: hammered copper
  Diameter: 34 cm base model
  Care: hand wash only
  Pairing: tea service and sweets
type: product
layout: product
date: 2026-04-04
blocks:
  - type: rich_text
    content:
      title: Runtime-ready, not runtime-dependent
      html: |
        <p>The storefront remains pre-rendered and cacheable, while the payment path can still talk to an external gateway or internal runtime service.</p>
  - type: faq
    content:
      title: Why this page matters
    items:
      - question: Does the product page need server-side rendering?
        answer: No. The layout is built statically and only the secure checkout hand-off is dynamic.
      - question: Where should inventory or tax logic live?
        answer: Those concerns belong in provider adapters and runtime services rather than the core generator.
---

If you later add inventory, shipping, or tax logic, those belong in provider adapters and runtime services rather than in the core generator.
