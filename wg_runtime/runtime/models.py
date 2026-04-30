import uuid
from decimal import Decimal
from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=240)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_published = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class ProductVariant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    sku = models.CharField(max_length=120, unique=True)
    label = models.CharField(max_length=180)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=12, default="USD")
    is_published = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sku"]

    def __str__(self) -> str:
        return f"{self.product.name} ({self.sku})"


class InventoryItem(models.Model):
    variant = models.OneToOneField(ProductVariant, on_delete=models.CASCADE, related_name="inventory")
    sku = models.CharField(max_length=120)
    available_quantity = models.IntegerField(default=0)
    reserved_quantity = models.IntegerField(default=0)
    policy = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sku"]

    def __str__(self) -> str:
        return f"Inventory {self.sku}"


def _generate_unique_id() -> str:
    return uuid.uuid4().hex


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_CANCELLED = "cancelled"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_FAILED, "Failed"),
    ]

    order_id = models.CharField(max_length=64, unique=True, default=_generate_unique_id)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=12, default="USD")
    provider = models.CharField(max_length=120, blank=True)
    success_url = models.URLField(blank=True)
    failure_url = models.URLField(blank=True)
    status_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.order_id


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="lines")
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=240)
    sku = models.CharField(max_length=120)
    quantity = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=12, default="USD")
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.title} x {self.quantity}"


class PaymentAttempt(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payment_attempts")
    attempt_id = models.CharField(max_length=64, default=_generate_unique_id)
    provider = models.CharField(max_length=120, blank=True)
    reference = models.CharField(max_length=128, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=12, default="USD")
    status = models.CharField(max_length=24, choices=STATUS_CHOICES, default=STATUS_PENDING)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.attempt_id} ({self.status})"


class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="refunds")
    payment_attempt = models.ForeignKey(PaymentAttempt, on_delete=models.SET_NULL, null=True, blank=True)
    refund_id = models.CharField(max_length=64, default=_generate_unique_id)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=12, default="USD")
    status = models.CharField(max_length=24, default="pending")
    reason = models.CharField(max_length=240, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.refund_id


class AuditEvent(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    actor = models.CharField(max_length=192, blank=True)
    action = models.CharField(max_length=120)
    model_name = models.CharField(max_length=120, blank=True)
    object_id = models.CharField(max_length=128, blank=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.action} @ {self.timestamp.isoformat()}"


class MediaAsset(models.Model):
    title = models.CharField(max_length=240)
    file_name = models.CharField(max_length=240)
    file_url = models.URLField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["title"]

    def __str__(self) -> str:
        return self.title
