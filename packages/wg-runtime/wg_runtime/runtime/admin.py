from __future__ import annotations

from django import forms
from django.contrib import admin

from .audit import get_actor_label, log_audit_event, log_model_audit_event
from .integrations.outbox import requeue_dead_letter_event
from .models import (
    AuditEvent,
    IntegrationOutboxEvent,
    InventoryAdjustment,
    InventoryItem,
    MediaAsset,
    Order,
    OrderLine,
    PaymentAttempt,
    Product,
    ProductVariant,
    Refund,
)


def _model_field_names(model_cls) -> list[str]:
    names = [field.name for field in model_cls._meta.fields]
    names.extend(field.name for field in model_cls._meta.many_to_many)
    return names


class AdminAuditMixin:
    """Logs CRUD actions performed through Django admin."""

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        action = "admin.update" if change else "admin.create"
        log_model_audit_event(
            action=action,
            user=request.user,
            instance=obj,
            description=f"{obj.__class__.__name__} {'updated' if change else 'created'} from admin.",
            metadata={"source": "django_admin"},
        )

    def delete_model(self, request, obj):
        object_id = str(getattr(obj, "pk", "") or "")
        model_name = obj.__class__.__name__
        actor = get_actor_label(request.user)
        log_audit_event(
            action="admin.delete",
            actor=actor,
            model_name=model_name,
            object_id=object_id,
            description=f"{model_name} deleted from admin.",
            metadata={"source": "django_admin"},
        )
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        actor = get_actor_label(request.user)
        model_name = self.model.__name__
        object_ids = [str(value) for value in queryset.values_list("pk", flat=True)]
        for object_id in object_ids:
            log_audit_event(
                action="admin.delete",
                actor=actor,
                model_name=model_name,
                object_id=object_id,
                description=f"{model_name} deleted from admin (bulk action).",
                metadata={"source": "django_admin", "bulk": True},
            )
        super().delete_queryset(request, queryset)


class ReadOnlyAdminMixin:
    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return _model_field_names(self.model)


class ReadOnlyInlineMixin:
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return _model_field_names(self.model)


@admin.register(Product)
class ProductAdmin(AdminAuditMixin, admin.ModelAdmin):
    list_display = ["name", "slug", "is_published", "created_at", "updated_at"]
    search_fields = ["name", "slug"]
    list_filter = ["is_published", "created_at", "updated_at"]
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ProductVariant)
class ProductVariantAdmin(AdminAuditMixin, admin.ModelAdmin):
    list_display = ["sku", "label", "product", "price", "currency", "is_published", "updated_at"]
    search_fields = ["sku", "label", "product__name"]
    list_filter = ["is_published", "currency", "updated_at"]
    readonly_fields = ["created_at", "updated_at"]


class InventoryItemAdminForm(forms.ModelForm):
    adjustment_reason = forms.CharField(
        required=False,
        max_length=280,
        help_text="Reason for this stock adjustment (saved to adjustment and audit logs).",
    )

    class Meta:
        model = InventoryItem
        fields = "__all__"


@admin.register(InventoryItem)
class InventoryItemAdmin(AdminAuditMixin, admin.ModelAdmin):
    form = InventoryItemAdminForm
    list_display = [
        "sku",
        "variant",
        "available_quantity",
        "reserved_quantity",
        "policy",
        "updated_at",
    ]
    search_fields = ["sku"]
    list_filter = ["policy", "updated_at"]
    readonly_fields = ["updated_at"]

    def save_model(self, request, obj, form, change):
        previous_state = None
        if change and obj.pk:
            previous_state = InventoryItem.objects.filter(pk=obj.pk).values(
                "available_quantity", "reserved_quantity"
            ).first()

        super().save_model(request, obj, form, change)

        if not previous_state:
            return

        old_available = int(previous_state.get("available_quantity", 0))
        old_reserved = int(previous_state.get("reserved_quantity", 0))
        new_available = int(obj.available_quantity)
        new_reserved = int(obj.reserved_quantity)

        if old_available == new_available and old_reserved == new_reserved:
            return

        delta_available = new_available - old_available
        delta_reserved = new_reserved - old_reserved
        reason = str(form.cleaned_data.get("adjustment_reason", "")).strip()
        actor = get_actor_label(request.user)

        InventoryAdjustment.objects.create(
            inventory_item=obj,
            old_available_quantity=old_available,
            new_available_quantity=new_available,
            delta_available_quantity=delta_available,
            old_reserved_quantity=old_reserved,
            new_reserved_quantity=new_reserved,
            delta_reserved_quantity=delta_reserved,
            actor=actor,
            reason=reason,
            metadata={"source": "django_admin"},
        )

        log_audit_event(
            action="admin.inventory_adjust",
            actor=actor,
            model_name="InventoryItem",
            object_id=str(obj.pk),
            description=f"Adjusted stock for {obj.sku}.",
            metadata={
                "source": "django_admin",
                "sku": obj.sku,
                "old_available_quantity": old_available,
                "new_available_quantity": new_available,
                "delta_available_quantity": delta_available,
                "old_reserved_quantity": old_reserved,
                "new_reserved_quantity": new_reserved,
                "delta_reserved_quantity": delta_reserved,
                "reason": reason,
            },
        )


class OrderLineInline(ReadOnlyInlineMixin, admin.TabularInline):
    model = OrderLine
    fields = [
        "title",
        "sku",
        "quantity",
        "price",
        "currency",
        "variant",
        "metadata",
    ]


class PaymentAttemptInline(ReadOnlyInlineMixin, admin.TabularInline):
    model = PaymentAttempt
    fields = [
        "attempt_id",
        "provider",
        "reference",
        "amount",
        "currency",
        "status",
        "metadata",
        "created_at",
    ]


@admin.register(Order)
class OrderAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ["order_id", "status", "total_amount", "currency", "provider", "created_at"]
    search_fields = ["order_id", "provider", "status"]
    list_filter = ["status", "currency", "provider", "created_at"]
    inlines = [OrderLineInline, PaymentAttemptInline]


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ["attempt_id", "order", "provider", "reference", "amount", "currency", "status", "created_at"]
    search_fields = ["attempt_id", "order__order_id", "reference", "provider"]
    list_filter = ["status", "currency", "provider", "created_at"]


@admin.register(Refund)
class RefundAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ["refund_id", "order", "amount", "currency", "status", "created_at"]
    search_fields = ["refund_id", "order__order_id"]
    list_filter = ["status", "currency", "created_at"]


@admin.register(AuditEvent)
class AuditEventAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ["timestamp", "actor", "action", "model_name", "object_id"]
    search_fields = ["actor", "action", "model_name", "object_id"]
    list_filter = ["actor", "action", "model_name", "timestamp"]


@admin.register(InventoryAdjustment)
class InventoryAdjustmentAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = [
        "created_at",
        "inventory_item",
        "delta_available_quantity",
        "delta_reserved_quantity",
        "actor",
        "reason",
    ]
    search_fields = ["inventory_item__sku", "actor", "reason"]
    list_filter = ["created_at", "actor"]


@admin.register(MediaAsset)
class MediaAssetAdmin(AdminAuditMixin, admin.ModelAdmin):
    list_display = ["title", "file_name", "file_url", "media_file", "created_at"]
    search_fields = ["title", "file_name"]
    list_filter = ["created_at"]
    readonly_fields = ["created_at"]


@admin.register(IntegrationOutboxEvent)
class IntegrationOutboxEventAdmin(admin.ModelAdmin):
    list_display = [
        "created_at",
        "event_type",
        "provider_domain",
        "provider_name",
        "status",
        "attempts",
        "max_attempts",
        "next_attempt_at",
    ]
    search_fields = ["event_type", "provider_domain", "provider_name", "idempotency_key"]
    list_filter = ["status", "provider_domain", "provider_name", "event_type", "created_at"]
    readonly_fields = _model_field_names(IntegrationOutboxEvent)
    actions = ["requeue_dead_letter_events"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        if obj is None:
            return request.user.has_perm(
                "runtime.change_integrationoutboxevent"
            ) or request.user.has_perm("runtime.view_integrationoutboxevent")
        return False

    @admin.action(description="Requeue selected dead-letter integration events")
    def requeue_dead_letter_events(self, request, queryset):
        requeued = 0
        for event in queryset:
            if event.status != IntegrationOutboxEvent.STATUS_DEAD_LETTER:
                continue
            requeue_dead_letter_event(event.id)
            requeued += 1
        self.message_user(request, f"Requeued {requeued} dead-letter events.")
