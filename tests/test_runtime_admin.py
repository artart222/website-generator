import os
import sys
import tempfile
import uuid
from pathlib import Path

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wg_runtime.settings")

import django  # noqa: E402
from django.conf import settings  # noqa: E402

temp_db = Path(tempfile.gettempdir()) / f"wg_runtime_admin_test_{os.getpid()}.sqlite3"
if temp_db.exists():
    temp_db.unlink()
settings.DATABASES["default"]["NAME"] = str(temp_db)
if not django.apps.apps.ready:
    django.setup()

from django.contrib.auth import get_user_model  # noqa: E402
from django.contrib.auth.models import Group  # noqa: E402
from django.core.management import call_command  # noqa: E402
from django.db import connections  # noqa: E402
from django.test import Client  # noqa: E402
from django.urls import reverse  # noqa: E402

from wg_runtime.runtime.models import (  # noqa: E402
    AuditEvent,
    InventoryAdjustment,
    InventoryItem,
    MediaAsset,
    Order,
    PaymentAttempt,
    Product,
    ProductVariant,
    Refund,
)
connections.close_all()
call_command("migrate", verbosity=0, interactive=False)


def _unique_username(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _create_user(
    *,
    username: str,
    password: str = "secret12345",
    is_staff: bool = False,
    is_superuser: bool = False,
):
    user_model = get_user_model()
    user = user_model.objects.create_user(
        username=username,
        password=password,
    )
    user.is_staff = is_staff
    user.is_superuser = is_superuser
    user.save(update_fields=["is_staff", "is_superuser"])
    return user


def test_admin_login_required_and_staff_user_can_access_admin_index():
    client = Client()
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/admin/login/" in response.url

    superuser = _create_user(
        username=_unique_username("superuser"),
        is_staff=True,
        is_superuser=True,
    )
    client.force_login(superuser)
    admin_response = client.get("/admin/")
    assert admin_response.status_code == 200


def test_bootstrap_runtime_roles_is_idempotent_and_assigns_expected_permissions():
    call_command("bootstrap_runtime_roles", verbosity=0)
    call_command("bootstrap_runtime_roles", verbosity=0)

    expected_groups = {"admin", "editor", "merchandiser", "support"}
    actual_groups = set(Group.objects.filter(name__in=expected_groups).values_list("name", flat=True))
    assert actual_groups == expected_groups

    admin_user = _create_user(username=_unique_username("admin_role"), is_staff=True)
    editor_user = _create_user(username=_unique_username("editor_role"), is_staff=True)
    merch_user = _create_user(username=_unique_username("merch_role"), is_staff=True)
    support_user = _create_user(username=_unique_username("support_role"), is_staff=True)

    admin_user.groups.add(Group.objects.get(name="admin"))
    editor_user.groups.add(Group.objects.get(name="editor"))
    merch_user.groups.add(Group.objects.get(name="merchandiser"))
    support_user.groups.add(Group.objects.get(name="support"))

    assert admin_user.has_perm("runtime.change_product")
    assert admin_user.has_perm("runtime.delete_mediaasset")
    assert admin_user.has_perm("runtime.view_order")
    assert not admin_user.has_perm("runtime.change_order")
    assert not admin_user.has_perm("runtime.delete_paymentattempt")

    assert editor_user.has_perm("runtime.change_product")
    assert editor_user.has_perm("runtime.view_inventoryitem")
    assert not editor_user.has_perm("runtime.change_inventoryitem")
    assert not editor_user.has_perm("runtime.delete_product")

    assert merch_user.has_perm("runtime.change_inventoryitem")
    assert merch_user.has_perm("runtime.change_productvariant")
    assert merch_user.has_perm("runtime.view_paymentattempt")
    assert not merch_user.has_perm("runtime.delete_inventoryitem")

    assert support_user.has_perm("runtime.view_order")
    assert support_user.has_perm("runtime.view_product")
    assert not support_user.has_perm("runtime.add_order")
    assert not support_user.has_perm("runtime.change_product")

    assigned_user = _create_user(
        username=_unique_username("assigned_user"),
        is_staff=False,
    )
    call_command(
        "bootstrap_runtime_roles",
        "--assign-user",
        assigned_user.username,
        "--assign-role",
        "support",
        verbosity=0,
    )
    assigned_user.refresh_from_db()
    assert assigned_user.is_staff is True
    assert assigned_user.groups.filter(name="support").exists()


def test_inventory_admin_change_creates_adjustment_and_audit_event():
    superuser = _create_user(
        username=_unique_username("inventory_superuser"),
        is_staff=True,
        is_superuser=True,
    )

    product = Product.objects.create(name="Admin Stock Product", slug=f"admin-stock-{uuid.uuid4().hex[:8]}")
    variant = ProductVariant.objects.create(
        product=product,
        sku=f"SKU-{uuid.uuid4().hex[:6]}",
        label="Default Variant",
        price="10.00",
        currency="USD",
    )
    inventory = InventoryItem.objects.create(
        variant=variant,
        sku=variant.sku,
        available_quantity=10,
        reserved_quantity=1,
        policy="manual",
    )

    client = Client()
    client.force_login(superuser)

    change_url = reverse("admin:runtime_inventoryitem_change", args=[inventory.pk])
    response = client.post(
        change_url,
        {
            "variant": variant.pk,
            "sku": inventory.sku,
            "available_quantity": 14,
            "reserved_quantity": 2,
            "policy": "manual",
            "metadata": "{}",
            "adjustment_reason": "Cycle count correction",
            "_save": "Save",
        },
        follow=True,
    )

    assert response.status_code == 200

    adjustments = InventoryAdjustment.objects.filter(inventory_item=inventory)
    assert adjustments.count() == 1
    adjustment = adjustments.first()
    assert adjustment is not None
    assert adjustment.old_available_quantity == 10
    assert adjustment.new_available_quantity == 14
    assert adjustment.delta_available_quantity == 4
    assert adjustment.old_reserved_quantity == 1
    assert adjustment.new_reserved_quantity == 2
    assert adjustment.delta_reserved_quantity == 1
    assert adjustment.reason == "Cycle count correction"

    audit_event = AuditEvent.objects.filter(
        action="admin.inventory_adjust",
        model_name="InventoryItem",
        object_id=str(inventory.pk),
    ).first()
    assert audit_event is not None
    assert "Adjusted stock" in audit_event.description
    assert audit_event.actor == superuser.username


def test_order_payment_refund_admin_pages_are_inspection_only_for_admin_group_users():
    call_command("bootstrap_runtime_roles", verbosity=0)
    admin_group_user = _create_user(
        username=_unique_username("admin_group_user"),
        is_staff=True,
    )
    admin_group_user.groups.add(Group.objects.get(name="admin"))

    order = Order.objects.create(provider="local")
    payment = PaymentAttempt.objects.create(
        order=order,
        provider="local",
        amount=order.total_amount,
        currency=order.currency,
    )
    refund = Refund.objects.create(
        order=order,
        payment_attempt=payment,
        amount="1.00",
        currency="USD",
    )

    client = Client()
    client.force_login(admin_group_user)

    order_list_response = client.get(reverse("admin:runtime_order_changelist"))
    order_detail_response = client.get(reverse("admin:runtime_order_change", args=[order.pk]))
    order_add_response = client.get(reverse("admin:runtime_order_add"))

    assert order_list_response.status_code == 200
    assert order_detail_response.status_code == 200
    assert order_add_response.status_code == 403

    order_post_response = client.post(
        reverse("admin:runtime_order_change", args=[order.pk]),
        {
            "order_id": order.order_id,
            "status": Order.STATUS_PENDING,
            "total_amount": str(order.total_amount),
            "currency": order.currency,
            "provider": order.provider,
            "success_url": order.success_url,
            "failure_url": order.failure_url,
            "status_url": order.status_url,
            "metadata": "{}",
            "_save": "Save",
        },
    )
    assert order_post_response.status_code == 403

    payment_detail_response = client.get(reverse("admin:runtime_paymentattempt_change", args=[payment.pk]))
    refund_detail_response = client.get(reverse("admin:runtime_refund_change", args=[refund.pk]))
    assert payment_detail_response.status_code == 200
    assert refund_detail_response.status_code == 200

    assert not admin_group_user.has_perm("runtime.change_order")
    assert not admin_group_user.has_perm("runtime.change_paymentattempt")
    assert not admin_group_user.has_perm("runtime.change_refund")


def test_audit_views_are_read_only_for_admin_group_users():
    call_command("bootstrap_runtime_roles", verbosity=0)
    admin_group_user = _create_user(
        username=_unique_username("audit_admin_user"),
        is_staff=True,
    )
    admin_group_user.groups.add(Group.objects.get(name="admin"))

    event = AuditEvent.objects.create(
        actor="system",
        action="admin.create",
        model_name="Product",
        object_id="123",
        description="Created via test fixture.",
    )

    client = Client()
    client.force_login(admin_group_user)

    changelist_response = client.get(reverse("admin:runtime_auditevent_changelist"))
    detail_response = client.get(reverse("admin:runtime_auditevent_change", args=[event.pk]))
    assert changelist_response.status_code == 200
    assert detail_response.status_code == 200

    post_response = client.post(
        reverse("admin:runtime_auditevent_change", args=[event.pk]),
        {
            "actor": event.actor,
            "action": event.action,
            "model_name": event.model_name,
            "object_id": event.object_id,
            "description": "Mutated",
            "metadata": "{}",
            "_save": "Save",
        },
    )
    assert post_response.status_code == 403

    media_field = MediaAsset._meta.get_field("media_file")
    assert media_field.blank is True
