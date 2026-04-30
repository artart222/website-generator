from django.contrib import admin
from .models import (
    AuditEvent,
    InventoryItem,
    MediaAsset,
    Order,
    OrderLine,
    PaymentAttempt,
    Product,
    ProductVariant,
    Refund,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "created_at", "updated_at"]
    search_fields = ["name", "slug"]


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = ["sku", "label", "product", "price", "currency"]
    search_fields = ["sku", "label", "product__name"]


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ["sku", "available_quantity", "reserved_quantity", "policy"]
    search_fields = ["sku"]


class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0


class PaymentAttemptInline(admin.TabularInline):
    model = PaymentAttempt
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["order_id", "status", "total_amount", "currency", "created_at"]
    search_fields = ["order_id", "provider", "status"]
    inlines = [OrderLineInline, PaymentAttemptInline]


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ["refund_id", "order", "amount", "currency", "status", "created_at"]
    search_fields = ["refund_id", "order__order_id"]


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["timestamp", "actor", "action", "model_name"]
    search_fields = ["actor", "action", "model_name", "object_id"]


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ["title", "file_name", "created_at"]
    search_fields = ["title", "file_name"]
