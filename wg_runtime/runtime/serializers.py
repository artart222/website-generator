from rest_framework import serializers


class CheckoutSessionInputSerializer(serializers.Serializer):
    provider = serializers.CharField(required=False, allow_blank=True, default="")
    currency = serializers.CharField(default="USD")
    metadata = serializers.DictField(child=serializers.JSONField(), required=False, default=dict)
    success_url = serializers.URLField(required=False, allow_blank=True, default="")
    failure_url = serializers.URLField(required=False, allow_blank=True, default="")
    status_url = serializers.URLField(required=False, allow_blank=True, default="")
    lines = serializers.ListField(
        child=serializers.DictField(child=serializers.JSONField()),
        min_length=1,
    )


class CheckoutSessionResponseSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    status = serializers.CharField()
    redirect_url = serializers.CharField()
    payment_reference = serializers.CharField()


class OrderLineSerializer(serializers.Serializer):
    title = serializers.CharField()
    sku = serializers.CharField()
    quantity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()


class OrderStatusSerializer(serializers.Serializer):
    order_id = serializers.CharField()
    status = serializers.CharField()
    subtotal_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    tax_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    shipping_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    provider = serializers.CharField()
    lines = OrderLineSerializer(many=True)
    metadata = serializers.DictField(child=serializers.JSONField(), required=False, default=dict)


class ProductVariantSerializer(serializers.Serializer):
    sku = serializers.CharField()
    label = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    metadata = serializers.DictField(child=serializers.JSONField(), required=False, default=dict)


class ProductCatalogSerializer(serializers.Serializer):
    id = serializers.CharField(required=False)
    name = serializers.CharField()
    slug = serializers.CharField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.DictField(child=serializers.JSONField(), required=False, default=dict)
    variants = ProductVariantSerializer(many=True)


class CatalogSnapshotSerializer(serializers.Serializer):
    products = ProductCatalogSerializer(many=True)
