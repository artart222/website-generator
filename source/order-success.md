---
title: Order Confirmed
summary: Static success page shown after runtime payment verification.
description: Example success page for a checkout flow.
date: 2026-04-04
type: page
layout: document
blocks:
  - type: cta
    content:
      title: Payment verified
      text: Your runtime adapter can redirect customers here after confirming the payment with the gateway.
      action:
        label: Check order status
        url: /order-status/
---

# Order Confirmed

This is a static page. The actual payment verification should happen in the runtime callback handler.
