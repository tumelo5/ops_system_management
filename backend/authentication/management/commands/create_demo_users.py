from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

DEMO_USERS = [
    {
        "username": "demo_warehouse",
        "password": "Demo@1234",
        "first_name": "Demo",
        "last_name": "Warehouse",
        "email": "demo.warehouse@opsystem.demo",
        "department": "warehouse",
        "is_demo": True,
    },
    {
        "username": "demo_repairs",
        "password": "Demo@1234",
        "first_name": "Demo",
        "last_name": "Repairs",
        "email": "demo.repairs@opsystem.demo",
        "department": "repairs",
        "is_demo": True,
    },
    {
        "username": "demo_stores",
        "password": "Demo@1234",
        "first_name": "Demo",
        "last_name": "Stores",
        "email": "demo.stores@opsystem.demo",
        "department": "stores",
        "is_demo": True,
    },
    {
        "username": "demo_finance",
        "password": "Demo@1234",
        "first_name": "Demo",
        "last_name": "Finance",
        "email": "demo.finance@opsystem.demo",
        "department": "finance",
        "is_demo": True,
    },
]


class Command(BaseCommand):
    help = "Creates pre-defined demo users for employer previews."

    def handle(self, *args, **kwargs):
        created_count = 0
        skipped_count = 0

        for user_data in DEMO_USERS:
            username = user_data["username"]

            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f"  Skipped  : {username} (already exists)")
                )
                skipped_count += 1
                continue

            user = User.objects.create_user(
                username=username,
                password=user_data["password"],
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                email=user_data["email"],
                department=user_data["department"],
                is_demo=user_data["is_demo"],
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  Created  : {user.username} → {user.department}"
                )
            )
            created_count += 1

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {created_count} demo user(s) created, {skipped_count} skipped."
            )
        )