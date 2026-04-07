---
title: Bazaar Atelier
summary: Static-first storefront demo with product pages, cart islands, and runtime-backed checkout wiring.
description: A shop example built on the website generator's new extension, frontend, and runtime architecture.
authors:
  - Artin Mobasher
date: 2026-04-04
type: index
layout: document
blocks:
  - type: hero
    variant: splash
    content:
      eyebrow: Static-first commerce demo
      title: Bazaar Atelier sells like a store while still building like a static site
      text: Product pages, journal entries, and landing pages stay static. Checkout, payment verification, and order status are modeled as runtime integrations.
      actions:
        - label: Browse the shop
          url: /shop/
        - label: Track an order
          url: /order-status/
  - type: rich_text
    content:
      title: What this demo proves
      html: |
        <p>This repository now includes a storefront example that uses <strong>typed product content</strong>, a <strong>frontend island bundle</strong>, and a <strong>runtime target contract</strong>.</p>
        <p>The payment wiring is intentionally runtime-first, so an Iranian gateway adapter can own checkout session creation and callback verification without forcing the generator core to become a backend framework.</p>
  - type: commerce/cart
    content:
      title: Cart island placeholder
      text: The page is statically rendered, but the cart area is ready for a client-side island to mount interactive behavior.
  - type: faq
    content:
      title: How checkout works here
    items:
      - question: Are product pages static?
        answer: Yes. Catalog pages and product detail pages are generated at build time.
      - question: Where does payment happen?
        answer: Checkout is created through the configured runtime target, which can then redirect the customer to an Iranian gateway provider.
      - question: What happens after payment?
        answer: The gateway callback is verified by runtime code, and the static order-status page can read a public order state endpoint.
  - type: cta
    content:
      title: Want to inspect the product flow?
      text: Open a product page to see model-backed metadata and a checkout block rendered into the page.
      action:
        label: Open the catalog
        url: /shop/
---

# Bazaar Atelier

This homepage is intentionally hybrid: the storytelling stays static, while the transactional pieces are prepared for runtime integrations.

If you want to extend this demo, the next natural step is to build the runtime companion that listens on `commerce-api` and handles `iran_gateway` callbacks.
