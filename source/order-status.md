---
title: Order Status
summary: Public order lookup surface for the runtime order-state API.
description: Example page that would read public order state from the configured runtime target.
date: 2026-04-04
type: order-status
layout: document
blocks:
  - type: commerce/order_status
    content:
      title: Check your order
      text: This block is where a runtime-backed order status widget can mount.
    settings:
      runtime_target: commerce-api
  - type: faq
    content:
      title: What this page is for
    items:
      - question: Does this page contain secure order logic?
        answer: No. It is a static page designed to host a public status lookup tied to a runtime endpoint.
      - question: Why make order status public-only?
        answer: The generator should only ship public data here. Sensitive verification and payment state changes stay in runtime code.
---

# Order Status

Use this page as the hand-off point after a successful or failed payment callback has been processed by your backend runtime.
