---
title: Payment Not Completed
summary: Static failure page for interrupted or declined checkouts.
description: Example failure page for a checkout flow.
date: 2026-04-04
type: page
layout: document
blocks:
  - type: cta
    content:
      title: Payment was not completed
      text: If a gateway declines or cancels the payment, your runtime flow can redirect back here.
      action:
        label: Return to the shop
        url: /shop/
---

# Payment Not Completed

This page gives the shopper a clean way back into the storefront without embedding gateway logic into the static build.
