
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import timedelta



from backend.warehouse.models import (
    Client,
    DeviceModel,
    DeviceModelVersion,
    Batch,
    DeviceStaging,
    Device,
    DeviceRental,
   
)
from backend.warehouse.services import (
    DeviceNotFound, DeviceRentalService, RentalConflict)
from backend.authentication.models import CustomUser



User = get_user_model()

WAREHOUSE_DEPT = "warehouse"  # <-- adjust to match your actual department value

# BulkClientsView edge cases ---
class BulkClientsEdgeCaseTests(TestCase):

    def setUp(self):
        self.client_api = APIClient()
        self.bulk_clients_url = reverse("clients-bulk-base")
        self.user = User.objects.create_user(
            username="warehouse_agent",
            password="testpass123",
            department=WAREHOUSE_DEPT,
        )
        self.client_api.force_authenticate(user=self.user)

    def _post(self, clients):
        return self.client_api.post(
            self.bulk_clients_url,
            {"clients": clients},
            format="json",
        )

    # --- 1. Empty submission ---
    def test_empty_client_list(self):
        """
        Currently: an empty list passes serializer validation (many=True with
        zero items is valid) and create_bulk_base loops over nothing.
        This documents current behavior — flag as a design question: should
        an empty submission actually be rejected as a 400 instead of a
        "successful" no-op 201?
        """
        response = self._post([])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Client.objects.count(), 0)
        self.assertEqual(DeviceModel.objects.count(), 0)

    # --- 2. Duplicate client_name within the same request (transaction rollback) ---
    def test_duplicate_client_name_in_same_batch_rolls_back_entire_transaction(self):
        """
        Both rows pass serializer validation individually (UniqueValidator only
        checks against existing DB rows, not against siblings in the same batch).
        The first Client.objects.create() succeeds; the second hits IntegrityError
        and raises ValueError. Because create_bulk_base is wrapped in
        @transaction.atomic, the ENTIRE batch — including the first, already-created
        row — must roll back. This test verifies that atomicity actually holds.
        """
        payload = [
            {"client_name": "FNB", "model_name": "N910"},
            {"client_name": "FNB", "model_name": "N950"},
        ]
        response = self._post(payload)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Client.objects.count(), 0, "First row should have rolled back too — atomicity violated.")
        self.assertEqual(DeviceModel.objects.count(), 0)

    # --- 3. client_name exceeding max_length ---
    def test_client_name_too_long_rejected_at_serializer_level(self):
        """
        Should fail fast at the serializer layer (400), never reaching the DB —
        this is the exact "app-level gatekeeper" pattern discussed earlier.
        Adjust the length below if your Client.client_name max_length isn't 255.
        """
        too_long_name = "A" * 256
        payload = [{"client_name": too_long_name, "model_name": "N910"}]
        response = self._post(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Client.objects.count(), 0)

    # --- 4. Missing required field ---
    def test_missing_model_name_field_rejected(self):
        payload = [{"client_name": "FNB"}]  # no model_name at all
        response = self._post(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Client.objects.count(), 0)

    def test_missing_client_name_field_rejected(self):
        payload = [{"model_name": "N910"}]  # no client_name at all
        response = self._post(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Client.objects.count(), 0)

    # --- 5. Empty string values ---
    def test_empty_string_client_name_rejected(self):
        payload = [{"client_name": "", "model_name": "N910"}]
        response = self._post(payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- 6. No server-side cap on row count (frontend caps at 5, backend does not) ---
    def test_no_server_side_row_limit_enforced(self):
        """
        The frontend's WarehousePage caps rows at 5 (MAX_ROWS), but nothing
        in BulkClientsView or the serializers enforces this server-side. This test
        documents that a direct API call CAN currently bypass that cap — flagging
        as a gap, not asserting it as desired behavior. If you decide the backend
        should also enforce a cap, this test should be updated to expect 400.
        """
        payload = [
            {"client_name": f"Client{i}", "model_name": f"Model{i}"}
            for i in range(10)
        ]
        response = self._post(payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Client.objects.count(), 10, "No server-side cap currently enforced — matches frontend gap.")

    # --- 7. Whitespace AND case variants are both caught as duplicates ---
    def test_whitespace_and_case_variants_caught_as_duplicates(self):
        """
        ClientSerializer.validate_client_name() applies value.strip().lower()
        in one step before checking Client.objects.filter(client_name=normalized).exists().
        This means BOTH whitespace-only and case-only variants of an existing
        client_name normalize to the same stored value and get rejected as
        duplicates (400) — not treated as distinct clients.
        """
        response1 = self._post([{"client_name": "FNB", "model_name": "N910"}])
        response2 = self._post([{"client_name": " FNB ", "model_name": "N910"}])
        response3 = self._post([{"client_name": "fnb", "model_name": "N910"}])

        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Client.objects.count(), 1, "Whitespace and case variants should both be caught as the same client.")

    # --- 8. Same model_name across different clients — should succeed (intentional design) ---
    def test_same_model_name_across_different_clients_allowed(self):
        """
        DeviceModel is intentionally NOT unique-checked by name — different
        clients can have devices with the same model name. Confirms that
        design decision actually holds in practice.
        """
        self._post([{"client_name": "FNB", "model_name": "N910"}])
        response = self._post([{"client_name": "Nedbank", "model_name": "N910"}])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # client_name/model_name are normalized to lowercase by the serializers
        # (see ClientSerializer.validate_client_name / DeviceModelSerializer.validate_model_name)
        self.assertEqual(DeviceModel.objects.filter(model_name="n910").count(), 2)

    # --- 9. Payload isn't a list at all (many=True expects a list) ---
    def test_non_list_payload_rejected_cleanly(self):
        """
        Sending a single dict instead of a list under "clients" should be
        rejected as a clean 400 by the ListSerializer's own type check —
        not crash as a 500.
        """
        response = self.client_api.post(
            self.bulk_clients_url,
            {"clients": {"client_name": "FNB", "model_name": "N910"}},  # dict, not list
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# BulkClientLinkingView edge case tests
class BulkClientsLinkingTests(APITestCase):

    def test_batch_is_linked_to_client_and_model_version_to_model(self):
        # Arrange
        user = CustomUser.objects.create_user(
            username="warehouse_agent",
            password="password123",
            department="warehouse"
        )

        self.client.force_authenticate(user=user)

        client = Client.objects.create(
            client_name="Absa"
        )

        model = DeviceModel.objects.create(
            model_name="N910"
        )

        payload = {
            "links": [
                {
                    "batch_code": "BATCH001",
                    "client": client.id,
                    "model": model.id,
                    "version": "V2.1",
                }
            ]
        }

        # Act
        response = self.client.post(
            reverse("clients-bulk-links"),
            payload,
            format="json"
        )

        # Assert
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED
        )

        batch = Batch.objects.get(
            batch_code="batch001"
        )

        model_version = DeviceModelVersion.objects.get(
            model=model,
            version="v2.1"
        )

        self.assertEqual(batch.client, client)
        self.assertEqual(batch.model_version, model_version)
        self.assertEqual(model_version.model, model)


# Device scanning and confirmation edge case tests
class DeviceScanningAndConfirmationTests(APITestCase):

    def test_scanned_device_can_be_confirmed(self):
        # Arrange
        user = CustomUser.objects.create_user(
            username="warehouse_agent",
            password="password123",
            department="warehouse"
        )

        self.client.force_authenticate(user=user)

        client = Client.objects.create(
            client_name="Absa"
        )

        model = DeviceModel.objects.create(
            model_name="N910"
        )

        model_version = DeviceModelVersion.objects.create(
            model=model,
            version="v2.1"
        )

        batch = Batch.objects.create(
            batch_code="batch001",
            client=client,
            model_version=model_version
        )

        serial_number = "batch001-000001"

        # Act 1 - Scan device
        scan_response = self.client.post(
            reverse("devices-scan"),
            {
                "serial_number": serial_number
            },
            format="json"
        )

        # Assert scan
        self.assertEqual(
            scan_response.status_code,
            status.HTTP_201_CREATED
        )

        staging = DeviceStaging.objects.get(
            serial_number=serial_number
        )

        self.assertEqual(
            staging.batch_code,
            batch.batch_code
        )

        self.assertEqual(
            staging.client_name,
            client.client_name
        )

        self.assertEqual(
            staging.model_name,
            model.model_name
        )

        self.assertEqual(
            staging.version_name,
            model_version.version
        )

        self.assertEqual(
            staging.status,
            "PENDING"
        )

        # Act 2 - Confirm scanned device
        confirm_response = self.client.post(
            reverse("devices-confirm"),
            {
                "serial_number": serial_number
            },
            format="json"
        )

        # Assert confirmation
        self.assertEqual(
            confirm_response.status_code,
            status.HTTP_200_OK
        )

        device = Device.objects.get(
            serial_number=serial_number
        )

        self.assertEqual(
            device.batch,
            batch
        )

        self.assertEqual(
            device.model,
            model
        )

        self.assertEqual(
            device.version,
            model_version
        )

        self.assertEqual(
            device.device_status,
            "ACTIVE"
        )

        staging.refresh_from_db()

        self.assertEqual(
            staging.status,
            "PROCESSED"
        )


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def make_model_version(tag):
    model = DeviceModel.objects.create(model_name=f"pax a920 {tag}")
    return DeviceModelVersion.objects.create(model=model, version="v1")

 
 
def make_batch(client, code):
    return Batch.objects.create(
        client=client, batch_code=code, model_version=make_model_version(code)
    )
 
 
def make_device(batch, sn, status="ACTIVE"):
    version = batch.model_version
    return Device.objects.create(
        serial_number=sn, model=version.model, version=version,
        batch=batch, device_status=status,
    )
 
class RentalTestBase(TestCase):
    def setUp(self):
        self.company = Client.objects.create(name="johndoe")
        self.absa = Client.objects.create(name="absa")
        self.fnb = Client.objects.create(name="fnb")
 
        override = override_settings(COMPANY_CLIENT_ID=self.company.pk)
        override.enable()
        self.addCleanup(override.disable)
 
        self.company_batch = make_batch(self.company, "CO1")
        self.client_batch = make_batch(self.absa, "AB1")
 
        self.dev1 = make_device(self.company_batch, "CO1-1")
        self.dev2 = make_device(self.company_batch, "CO1-2")
        self.client_owned = make_device(self.client_batch, "AB1-1")
 
    def item(self, device, client, expected=None):
        return {"device": device, "rental_client": client, "expected_return_date": expected}
 
 
# ---------------------------------------------------------------------------
# create_rentals
# ---------------------------------------------------------------------------
class CreateRentalsTests(RentalTestBase):
    def test_creates_rental_for_company_owned_device(self):
        rentals = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])
        self.assertEqual(len(rentals), 1)
        self.assertEqual(rentals[0].rental_client, self.absa)
        self.assertIsNone(rentals[0].returned_at)
 
    def test_bulk_creates_all(self):
        DeviceRentalService.create_rentals(
            [self.item(self.dev1, self.absa), self.item(self.dev2, self.fnb)]
        )
        self.assertEqual(DeviceRental.objects.count(), 2)
 
    def test_rejects_client_owned_device(self):
        with self.assertRaisesMessage(RentalConflict, "not company-owned"):
            DeviceRentalService.create_rentals([self.item(self.client_owned, self.fnb)])
        self.assertEqual(DeviceRental.objects.count(), 0)
 
    def test_rejects_renting_to_the_company_itself(self):
        with self.assertRaisesMessage(RentalConflict, "owns it"):
            DeviceRentalService.create_rentals([self.item(self.dev1, self.company)])
 
    def test_rejects_device_not_active(self):
        self.dev1.device_status = "DECOMMSISSIONED"
        self.dev1.save()
        with self.assertRaisesMessage(RentalConflict, "not available"):
            DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])
 
    def test_rejects_already_rented_device(self):
        DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])
        with self.assertRaisesMessage(RentalConflict, "already rented"):
            DeviceRentalService.create_rentals([self.item(self.dev1, self.fnb)])
 
    def test_rejects_same_device_twice_in_one_request(self):
        with self.assertRaisesMessage(RentalConflict, "more than once"):
            DeviceRentalService.create_rentals(
                [self.item(self.dev1, self.absa), self.item(self.dev1, self.fnb)]
            )
        self.assertEqual(DeviceRental.objects.count(), 0)
 
    def test_bulk_is_all_or_nothing(self):
        # first item is valid, second is client-owned -> nothing is saved
        with self.assertRaises(RentalConflict):
            DeviceRentalService.create_rentals(
                [self.item(self.dev1, self.absa), self.item(self.client_owned, self.fnb)]
            )
        self.assertEqual(DeviceRental.objects.count(), 0)
 
    def test_device_can_be_rented_again_after_rental_ended(self):
        first = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        DeviceRentalService.end_rental(first.pk, timezone.localdate())
        DeviceRentalService.create_rentals([self.item(self.dev1, self.fnb)])
        self.assertEqual(DeviceRental.objects.filter(device=self.dev1).count(), 2)
 
    def test_device_table_never_duplicated(self):
        before = Device.objects.count()
        DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])
        self.assertEqual(Device.objects.count(), before)
 
    def test_batch_client_unchanged_by_rental(self):
        DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])
        self.dev1.refresh_from_db()
        self.assertEqual(self.dev1.batch.client, self.company)
 
 
class ActiveRentalConstraintTests(RentalTestBase):
    def test_database_blocks_two_active_rentals_for_one_device(self):
        DeviceRental.objects.create(device=self.dev1, rental_client=self.absa)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DeviceRental.objects.create(device=self.dev1, rental_client=self.fnb)
 
    def test_database_allows_many_ended_rentals(self):
        today = timezone.localdate()
        DeviceRental.objects.create(device=self.dev1, rental_client=self.absa, returned_at=today)
        DeviceRental.objects.create(device=self.dev1, rental_client=self.fnb, returned_at=today)
        DeviceRental.objects.create(device=self.dev1, rental_client=self.absa)  # one active
        self.assertEqual(DeviceRental.objects.filter(device=self.dev1).count(), 3)
 
 
# ---------------------------------------------------------------------------
# end_rental / get_active_rental
# ---------------------------------------------------------------------------
class EndRentalTests(RentalTestBase):
    def setUp(self):
        super().setUp()
        self.rental = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        # pretend the rental started 10 days ago so back-dating can be tested
        DeviceRental.objects.filter(pk=self.rental.pk).update(
            start_date=timezone.now() - timedelta(days=10)
        )
 
    def test_ends_rental_with_selected_date(self):
        end = timezone.localdate() - timedelta(days=3)
        rental = DeviceRentalService.end_rental(self.rental.pk, end)
        self.assertEqual(rental.returned_at, end)
 
    def test_can_end_today(self):
        today = timezone.localdate()
        self.assertEqual(DeviceRentalService.end_rental(self.rental.pk, today).returned_at, today)
 
    def test_rejects_end_date_before_start(self):
        with self.assertRaisesMessage(RentalConflict, "before the rental start"):
            DeviceRentalService.end_rental(self.rental.pk, timezone.localdate() - timedelta(days=11))
 
    def test_rejects_future_end_date(self):
        with self.assertRaisesMessage(RentalConflict, "future"):
            DeviceRentalService.end_rental(self.rental.pk, timezone.localdate() + timedelta(days=1))
 
    def test_rejects_ending_twice(self):
        DeviceRentalService.end_rental(self.rental.pk, timezone.localdate())
        with self.assertRaisesMessage(RentalConflict, "already been ended"):
            DeviceRentalService.end_rental(self.rental.pk, timezone.localdate())
 
    def test_failed_end_leaves_rental_active(self):
        with self.assertRaises(RentalConflict):
            DeviceRentalService.end_rental(self.rental.pk, timezone.localdate() + timedelta(days=5))
        self.rental.refresh_from_db()
        self.assertIsNone(self.rental.returned_at)
 
 
class GetActiveRentalTests(RentalTestBase):
    def test_returns_active_rental_by_serial(self):
        rental = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        found = DeviceRentalService.get_active_rental("CO1-1")
        self.assertEqual(found.pk, rental.pk)
 
    def test_returns_none_when_not_rented(self):
        self.assertIsNone(DeviceRentalService.get_active_rental("CO1-1"))
 
    def test_returns_none_after_rental_ended(self):
        rental = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        DeviceRentalService.end_rental(rental.pk, timezone.localdate())
        self.assertIsNone(DeviceRentalService.get_active_rental("CO1-1"))
 
    def test_returns_none_for_unknown_serial(self):
        self.assertIsNone(DeviceRentalService.get_active_rental("NOPE"))
 
 
# ---------------------------------------------------------------------------
# Operational client resolution (rental first, then Batch client)
# NOTE: update the import/call if you move the resolver to a shared module.
# ---------------------------------------------------------------------------
class OperationalClientTests(RentalTestBase):
    def test_unknown_serial_is_rejected(self):
        with self.assertRaises(DeviceNotFound):
            DeviceRentalService.resolve_operational_client("NOPE")
 
    def test_no_rental_falls_back_to_batch_client(self):
        client, source = DeviceRentalService.resolve_operational_client("CO1-1")
        self.assertEqual((client, source), (self.company, "BATCH"))
 
    def test_client_owned_device_resolves_to_its_own_client(self):
        client, source = DeviceRentalService.resolve_operational_client("AB1-1")
        self.assertEqual((client, source), (self.absa, "BATCH"))
 
    def test_active_rental_wins_over_batch_client(self):
        DeviceRentalService.create_rentals([self.item(self.dev1, self.fnb)])
        client, source = DeviceRentalService.resolve_operational_client("CO1-1")
        self.assertEqual((client, source), (self.fnb, "RENTAL"))
 
    def test_after_rental_ends_falls_back_to_batch_client(self):
        rental = DeviceRentalService.create_rentals([self.item(self.dev1, self.fnb)])[0]
        DeviceRentalService.end_rental(rental.pk, timezone.localdate())
        client, source = DeviceRentalService.resolve_operational_client("CO1-1")
        self.assertEqual((client, source), (self.company, "BATCH"))
 
    def test_latest_renter_is_used_after_re_rental(self):
        first = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        DeviceRentalService.end_rental(first.pk, timezone.localdate())
        DeviceRentalService.create_rentals([self.item(self.dev1, self.fnb)])
        client, _ = DeviceRentalService.resolve_operational_client("CO1-1")
        self.assertEqual(client, self.fnb)
 
 
# ---------------------------------------------------------------------------
# API views (permissions, serializer validation, status codes)
# ---------------------------------------------------------------------------
def make_model_version(tag):
    model = DeviceModel.objects.create(model_name=f"pax a920 {tag}")
    return DeviceModelVersion.objects.create(model=model, version="v1")
 
 
def make_batch(client, code):
    return Batch.objects.create(
        client=client, batch_code=code, model_version=make_model_version(code)
    )
 
 
def make_device(batch, sn, status="ACTIVE"):
    # Device requires model + version as well as batch
    version = batch.model_version
    return Device.objects.create(
        serial_number=sn,
        model=version.model,
        version=version,
        batch=batch,
        device_status=status,
    )
 
 
class RentalTestBase(TestCase):
    def setUp(self):
        self.company = Client.objects.create(client_name="johndoe")
        self.absa = Client.objects.create(client_name="absa")
        self.fnb = Client.objects.create(client_name="fnb")
 
        override = override_settings(COMPANY_CLIENT_ID=self.company.pk)
        override.enable()
        self.addCleanup(override.disable)
 
        self.company_batch = make_batch(self.company, "CO1")
        self.client_batch = make_batch(self.absa, "AB1")
 
        self.dev1 = make_device(self.company_batch, "CO1-1")
        self.dev2 = make_device(self.company_batch, "CO1-2")
        self.client_owned = make_device(self.client_batch, "AB1-1")
 
    def item(self, device, client, expected=None):
        return {"device": device, "rental_client": client, "expected_return_date": expected}
 
 

# create_rentals

class CreateRentalsTests(RentalTestBase):
    def test_creates_rental_for_company_owned_device(self):
        rentals = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])
        self.assertEqual(len(rentals), 1)
        self.assertEqual(rentals[0].rental_client, self.absa)
        self.assertIsNone(rentals[0].returned_at)
 
    def test_bulk_creates_all(self):
        DeviceRentalService.create_rentals(
            [self.item(self.dev1, self.absa), self.item(self.dev2, self.fnb)]
        )
        self.assertEqual(DeviceRental.objects.count(), 2)
 
    def test_rejects_client_owned_device(self):
        with self.assertRaisesMessage(RentalConflict, "not company-owned"):
            DeviceRentalService.create_rentals([self.item(self.client_owned, self.fnb)])
        self.assertEqual(DeviceRental.objects.count(), 0)
 
    def test_rejects_renting_to_the_company_itself(self):
        with self.assertRaisesMessage(RentalConflict, "owns it"):
            DeviceRentalService.create_rentals([self.item(self.dev1, self.company)])
 
    def test_rejects_device_not_active(self):
        self.dev1.device_status = "DECOMMISSIONED"
        self.dev1.save()
        with self.assertRaisesMessage(RentalConflict, "not available"):
            DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])
 
    def test_rejects_already_rented_device(self):
        DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])
        with self.assertRaisesMessage(RentalConflict, "already rented"):
            DeviceRentalService.create_rentals([self.item(self.dev1, self.fnb)])
 
    def test_rejects_same_device_twice_in_one_request(self):
        with self.assertRaisesMessage(RentalConflict, "more than once"):
            DeviceRentalService.create_rentals(
                [self.item(self.dev1, self.absa), self.item(self.dev1, self.fnb)]
            )
        self.assertEqual(DeviceRental.objects.count(), 0)
 
    def test_bulk_is_all_or_nothing(self):
        # first item is valid, second is client-owned -> nothing is saved
        with self.assertRaises(RentalConflict):
            DeviceRentalService.create_rentals(
                [self.item(self.dev1, self.absa), self.item(self.client_owned, self.fnb)]
            )
        self.assertEqual(DeviceRental.objects.count(), 0)
 
    def test_device_can_be_rented_again_after_rental_ended(self):
        first = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        DeviceRentalService.end_rental(first.pk, timezone.localdate())
        DeviceRentalService.create_rentals([self.item(self.dev1, self.fnb)])
        self.assertEqual(DeviceRental.objects.filter(device=self.dev1).count(), 2)
 
    def test_device_table_never_duplicated(self):
        before = Device.objects.count()
        DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])
        self.assertEqual(Device.objects.count(), before)
 
    def test_batch_client_unchanged_by_rental(self):
        DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])
        self.dev1.refresh_from_db()
        self.assertEqual(self.dev1.batch.client, self.company)
 
 
class ActiveRentalConstraintTests(RentalTestBase):
    def test_database_blocks_two_active_rentals_for_one_device(self):
        DeviceRental.objects.create(device=self.dev1, rental_client=self.absa)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                DeviceRental.objects.create(device=self.dev1, rental_client=self.fnb)
 
    def test_database_allows_many_ended_rentals(self):
        today = timezone.localdate()
        DeviceRental.objects.create(device=self.dev1, rental_client=self.absa, returned_at=today)
        DeviceRental.objects.create(device=self.dev1, rental_client=self.fnb, returned_at=today)
        DeviceRental.objects.create(device=self.dev1, rental_client=self.absa)  # one active
        self.assertEqual(DeviceRental.objects.filter(device=self.dev1).count(), 3)
 
 
# ---------------------------------------------------------------------------
# end_rental / get_active_rental
# ---------------------------------------------------------------------------
class EndRentalTests(RentalTestBase):
    def setUp(self):
        super().setUp()
        self.rental = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        # pretend the rental started 10 days ago so back-dating can be tested
        DeviceRental.objects.filter(pk=self.rental.pk).update(
            start_date=timezone.now() - timedelta(days=10)
        )
 
    def test_ends_rental_with_selected_date(self):
        end = timezone.localdate() - timedelta(days=3)
        rental = DeviceRentalService.end_rental(self.rental.pk, end)
        self.assertEqual(rental.returned_at, end)
 
    def test_can_end_today(self):
        today = timezone.localdate()
        self.assertEqual(DeviceRentalService.end_rental(self.rental.pk, today).returned_at, today)
 
    def test_rejects_end_date_before_start(self):
        with self.assertRaisesMessage(RentalConflict, "before the rental start"):
            DeviceRentalService.end_rental(self.rental.pk, timezone.localdate() - timedelta(days=11))
 
    def test_rejects_future_end_date(self):
        with self.assertRaisesMessage(RentalConflict, "future"):
            DeviceRentalService.end_rental(self.rental.pk, timezone.localdate() + timedelta(days=1))
 
    def test_rejects_ending_twice(self):
        DeviceRentalService.end_rental(self.rental.pk, timezone.localdate())
        with self.assertRaisesMessage(RentalConflict, "already been ended"):
            DeviceRentalService.end_rental(self.rental.pk, timezone.localdate())
 
    def test_failed_end_leaves_rental_active(self):
        with self.assertRaises(RentalConflict):
            DeviceRentalService.end_rental(self.rental.pk, timezone.localdate() + timedelta(days=5))
        self.rental.refresh_from_db()
        self.assertIsNone(self.rental.returned_at)
 
 
class GetActiveRentalTests(RentalTestBase):
    def test_returns_active_rental_by_serial(self):
        rental = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        found = DeviceRentalService.get_active_rental("CO1-1")
        self.assertEqual(found.pk, rental.pk)
 
    def test_returns_none_when_not_rented(self):
        self.assertIsNone(DeviceRentalService.get_active_rental("CO1-1"))
 
    def test_returns_none_after_rental_ended(self):
        rental = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        DeviceRentalService.end_rental(rental.pk, timezone.localdate())
        self.assertIsNone(DeviceRentalService.get_active_rental("CO1-1"))
 
    def test_returns_none_for_unknown_serial(self):
        self.assertIsNone(DeviceRentalService.get_active_rental("NOPE"))
 
 
# ---------------------------------------------------------------------------
# Operational client resolution (rental first, then Batch client)
# NOTE: update the import/call if you move the resolver to a shared module.
# ---------------------------------------------------------------------------
class OperationalClientTests(RentalTestBase):
    def test_unknown_serial_is_rejected(self):
        with self.assertRaises(DeviceNotFound):
            DeviceRentalService.resolve_operational_client("NOPE")
 
    def test_no_rental_falls_back_to_batch_client(self):
        client, source = DeviceRentalService.resolve_operational_client("CO1-1")
        self.assertEqual((client, source), (self.company, "BATCH"))
 
    def test_client_owned_device_resolves_to_its_own_client(self):
        client, source = DeviceRentalService.resolve_operational_client("AB1-1")
        self.assertEqual((client, source), (self.absa, "BATCH"))
 
    def test_active_rental_wins_over_batch_client(self):
        DeviceRentalService.create_rentals([self.item(self.dev1, self.fnb)])
        client, source = DeviceRentalService.resolve_operational_client("CO1-1")
        self.assertEqual((client, source), (self.fnb, "RENTAL"))
 
    def test_after_rental_ends_falls_back_to_batch_client(self):
        rental = DeviceRentalService.create_rentals([self.item(self.dev1, self.fnb)])[0]
        DeviceRentalService.end_rental(rental.pk, timezone.localdate())
        client, source = DeviceRentalService.resolve_operational_client("CO1-1")
        self.assertEqual((client, source), (self.company, "BATCH"))
 
    def test_latest_renter_is_used_after_re_rental(self):
        first = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        DeviceRentalService.end_rental(first.pk, timezone.localdate())
        DeviceRentalService.create_rentals([self.item(self.dev1, self.fnb)])
        client, _ = DeviceRentalService.resolve_operational_client("CO1-1")
        self.assertEqual(client, self.fnb)
 
 
# ---------------------------------------------------------------------------
# API views (permissions, serializer validation, status codes)
# ---------------------------------------------------------------------------
class RentalApiTests(RentalTestBase):
    def setUp(self):
        super().setUp()
        self.api = APIClient()
        self.warehouse_user = CustomUser.objects.create_user(  # ADAPT
            username="wh", password="x", department="warehouse"
        )
        self.repairs_user = CustomUser.objects.create_user(  # ADAPT
            username="rp", password="x", department="repairs"
        )
        self.api.force_authenticate(self.warehouse_user)
 
        self.create_url = reverse("device-rental-create")
        self.active_url = reverse("device-rental-active")
        self.end_url = reverse("device-rental-end")
 
    def payload(self, device, client, **extra):
        return {"device": device.pk, "rental_client": client.pk, **extra}
 
    # --- create ---
    def test_create_returns_201(self):
        res = self.api.post(self.create_url, [self.payload(self.dev1, self.absa)], format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(DeviceRental.objects.count(), 1)
 
    def test_create_requires_warehouse_department(self):
        self.api.force_authenticate(self.repairs_user)
        res = self.api.post(self.create_url, [self.payload(self.dev1, self.absa)], format="json")
        self.assertEqual(res.status_code, 403)
        self.assertEqual(DeviceRental.objects.count(), 0)
 
    def test_create_rejects_empty_list(self):
        res = self.api.post(self.create_url, [], format="json")
        self.assertEqual(res.status_code, 400)
 
    def test_create_rejects_unknown_device(self):
        res = self.api.post(
            self.create_url, [{"device": 999999, "rental_client": self.absa.pk}], format="json"
        )
        self.assertEqual(res.status_code, 400)
 
    def test_create_rejects_client_owned_device(self):
        res = self.api.post(self.create_url, [self.payload(self.client_owned, self.fnb)], format="json")
        self.assertEqual(res.status_code, 409)
        self.assertEqual(DeviceRental.objects.count(), 0)
 
    def test_create_rejects_past_expected_return_date(self):
        past = (timezone.now() - timedelta(days=1)).isoformat()
        res = self.api.post(
            self.create_url,
            [self.payload(self.dev1, self.absa, expected_return_date=past)],
            format="json",
        )
        self.assertEqual(res.status_code, 400)
 
    def test_create_rejects_already_rented(self):
        DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])
        res = self.api.post(self.create_url, [self.payload(self.dev1, self.fnb)], format="json")
        self.assertEqual(res.status_code, 409)
 
    # --- lookup ---
    def test_lookup_returns_active_rental(self):
        rental = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        res = self.api.get(self.active_url, {"serial_number": "CO1-1"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["rental_id"], rental.pk)
        self.assertEqual(res.data["client"], "absa")
 
    def test_lookup_404_when_not_on_rent(self):
        res = self.api.get(self.active_url, {"serial_number": "CO1-1"})
        self.assertEqual(res.status_code, 404)
 
    def test_lookup_requires_warehouse_department(self):
        self.api.force_authenticate(self.repairs_user)
        res = self.api.get(self.active_url, {"serial_number": "CO1-1"})
        self.assertEqual(res.status_code, 403)
 
    # --- end ---
    def test_end_rental_success(self):
        rental = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        today = timezone.localdate().isoformat()
        res = self.api.post(self.end_url, {"rental_id": rental.pk, "end_date": today}, format="json")
        self.assertEqual(res.status_code, 200)
        rental.refresh_from_db()
        self.assertEqual(rental.returned_at, timezone.localdate())
 
    def test_end_rental_rejects_future_date(self):
        rental = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        future = (timezone.localdate() + timedelta(days=2)).isoformat()
        res = self.api.post(self.end_url, {"rental_id": rental.pk, "end_date": future}, format="json")
        self.assertEqual(res.status_code, 400)
 
    def test_end_rental_rejects_already_ended(self):
        rental = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        DeviceRentalService.end_rental(rental.pk, timezone.localdate())
        today = timezone.localdate().isoformat()
        res = self.api.post(self.end_url, {"rental_id": rental.pk, "end_date": today}, format="json")
        self.assertEqual(res.status_code, 400)  # serializer only accepts active rentals
 
    def test_end_rental_requires_warehouse_department(self):
        rental = DeviceRentalService.create_rentals([self.item(self.dev1, self.absa)])[0]
        self.api.force_authenticate(self.repairs_user)
        today = timezone.localdate().isoformat()
        res = self.api.post(self.end_url, {"rental_id": rental.pk, "end_date": today}, format="json")
        self.assertEqual(res.status_code, 403)
        rental.refresh_from_db()
        self.assertIsNone(rental.returned_at)
 