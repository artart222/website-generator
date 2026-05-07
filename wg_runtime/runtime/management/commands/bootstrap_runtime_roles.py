from __future__ import annotations

from collections.abc import Iterable

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

from wg_runtime.runtime.models import (
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

OPS_FULL = ("add", "change", "delete", "view")
OPS_EDIT = ("add", "change", "view")
OPS_VIEW = ("view",)

MODEL_REGISTRY = {
    "product": Product,
    "productvariant": ProductVariant,
    "inventoryitem": InventoryItem,
    "inventoryadjustment": InventoryAdjustment,
    "mediaasset": MediaAsset,
    "order": Order,
    "orderline": OrderLine,
    "paymentattempt": PaymentAttempt,
    "refund": Refund,
    "auditevent": AuditEvent,
    "integrationoutboxevent": IntegrationOutboxEvent,
}

ROLE_PERMISSIONS = {
    "admin": {
        "full": ["product", "productvariant", "inventoryitem", "mediaasset"],
        "edit": ["integrationoutboxevent"],
        "view": [
            "order",
            "orderline",
            "paymentattempt",
            "refund",
            "auditevent",
            "inventoryadjustment",
        ],
    },
    "editor": {
        "edit": ["product", "productvariant", "mediaasset"],
        "view": [
            "inventoryitem",
            "inventoryadjustment",
            "order",
            "orderline",
            "paymentattempt",
            "refund",
            "auditevent",
            "integrationoutboxevent",
        ],
    },
    "merchandiser": {
        "edit": ["product", "productvariant", "inventoryitem", "mediaasset"],
        "view": [
            "order",
            "orderline",
            "paymentattempt",
            "refund",
            "auditevent",
            "inventoryadjustment",
            "integrationoutboxevent",
        ],
    },
    "support": {
        "view": [
            "order",
            "orderline",
            "paymentattempt",
            "refund",
            "auditevent",
            "product",
            "productvariant",
            "inventoryitem",
            "mediaasset",
            "integrationoutboxevent",
        ],
    },
}


def _permission_codenames(model_key: str, operations: Iterable[str]) -> set[str]:
    model_cls = MODEL_REGISTRY[model_key]
    model_name = model_cls._meta.model_name
    return {f"{operation}_{model_name}" for operation in operations}


class Command(BaseCommand):
    help = "Create/update runtime role groups and assign model permissions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--assign-user",
            dest="assign_user",
            help="Optional username to assign to one role after bootstrapping.",
        )
        parser.add_argument(
            "--assign-role",
            dest="assign_role",
            choices=sorted(ROLE_PERMISSIONS.keys()),
            default="admin",
            help="Role used with --assign-user. Defaults to admin.",
        )

    def handle(self, *args, **options):
        role_names = sorted(ROLE_PERMISSIONS.keys())
        created_or_updated: list[str] = []

        for role_name in role_names:
            policy = ROLE_PERMISSIONS[role_name]
            group, _ = Group.objects.get_or_create(name=role_name)

            codenames: set[str] = set()
            for model_key in policy.get("full", []):
                codenames.update(_permission_codenames(model_key, OPS_FULL))
            for model_key in policy.get("edit", []):
                codenames.update(_permission_codenames(model_key, OPS_EDIT))
            for model_key in policy.get("view", []):
                codenames.update(_permission_codenames(model_key, OPS_VIEW))

            permissions = Permission.objects.filter(
                content_type__app_label="runtime",
                codename__in=sorted(codenames),
            )
            group.permissions.set(permissions)
            created_or_updated.append(role_name)

        self.stdout.write(
            self.style.SUCCESS(
                "Runtime roles bootstrapped: " + ", ".join(created_or_updated)
            )
        )

        assign_user = options.get("assign_user")
        assign_role = options.get("assign_role", "admin")
        if not assign_user:
            return

        UserModel = get_user_model()
        user = UserModel.objects.filter(username=assign_user).first()
        if user is None:
            raise CommandError(f"User '{assign_user}' does not exist.")

        role_group = Group.objects.get(name=assign_role)
        user.groups.add(role_group)
        if hasattr(user, "is_staff") and not user.is_staff:
            user.is_staff = True
            user.save(update_fields=["is_staff"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Assigned user '{assign_user}' to role '{assign_role}' and ensured staff access."
            )
        )
