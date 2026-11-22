"""
Rental and company endpoints: permissions, status codes, payloads, error contract.

The rules themselves are proven in test_rental_services.py; here we only check that each
endpoint reaches the service and reports the outcome correctly.
"""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from ..models import CompanyProfile, DeviceRental
from .base import RentalWorldMixin, WarehouseAPITestCase
from .factories import OTHER_DEPARTMENT, make_client, make_device, make_rental, make_user


def future(days=30):
    return (timezone.now() + timedelta(days=days)).isoformat()


# Assign rentals (bulk)
class AssignRentalApiTests(RentalWorldMixin, WarehouseAPITestCase):

    def setUp(self):
        super().setUp()
        self.build_rental_world()

    def post(self, rows):
        return self.client.post(reverse("device-rental-create"), rows, format="json")

    def row(self, device=None, client=None, **extra):
        return {
            "device": (device or self.device).serial_number,
            "rental_client": (client or self.customer).id,
            "expected_return_date": future(),
            **extra,
        }

    def test_rents_devices_and_returns_201_with_a_summary(self):
        second = make_device(batch=self.device.batch)

        response = self.post([self.row(), self.row(device=second)])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "2 device(s) rented out.")
        self.assertEqual(
            [(r["serial_number"], r["client"]) for r in response.data["rentals"]],
            [(self.device.serial_number, "customer"), (second.serial_number, "customer")],
        )
        self.assertEqual(DeviceRental.objects.filter(returned_at__isnull=True).count(), 2)

    def test_expected_return_date_is_required(self):
        missing = self.row()
        del missing["expected_return_date"]
        response = self.post([missing])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Choose an expected return date.")

        response = self.post([self.row(expected_return_date=None)])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Choose an expected return date.")
        self.assertEqual(DeviceRental.objects.count(), 0)

    def test_expected_return_date_in_the_past_returns_400(self):
        yesterday = (timezone.now() - timedelta(days=1)).isoformat()

        response = self.post([self.row(expected_return_date=yesterday)])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Expected return date must be in the future.")
        self.assertEqual(DeviceRental.objects.count(), 0)

    def test_invalid_expected_return_date_returns_400(self):
        response = self.post([self.row(expected_return_date="not a date")])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Expected return date must be a valid date.")

    def test_unknown_serial_number_returns_400(self):
        response = self.post([self.row() | {"device": "zzz"}])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "No device with serial number 'zzz' was found.")

    def test_unknown_or_missing_client_returns_400(self):
        unknown = self.post([self.row() | {"rental_client": 999999}])
        missing = self.post([{"device": self.device.serial_number, "expected_return_date": future()}])

        self.assertEqual(unknown.data["error"], "The selected client does not exist.")
        self.assertEqual(missing.data["error"], "Rental client is required.")

    def test_empty_list_returns_400(self):
        response = self.post([])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Add at least one row.")

    def test_more_than_fifty_rows_returns_400(self):
        response = self.post([{"device": "x", "rental_client": 1}] * 51)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "At most 50 rows can be submitted at once.")

    def test_same_device_twice_in_the_payload_returns_400(self):
        response = self.post([self.row(), self.row()])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], f"Device '{self.device.serial_number}' appears more than once.")

    def test_client_owned_device_returns_409_and_nothing_is_rented(self):
        response = self.post([self.row(), self.row(device=self.owned_device, client=make_client("other"))])

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("not company-owned", response.data["error"])
        self.assertEqual(DeviceRental.objects.count(), 0)

    def test_renting_to_the_company_itself_returns_409(self):
        response = self.post([self.row(client=self.company)])

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "A device cannot be rented to the company that owns it.")

    def test_device_already_on_rent_returns_409(self):
        make_rental(self.device, self.customer)

        response = self.post([self.row()])

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("already rented out", response.data["error"])

    def test_company_not_set_returns_409(self):
        CompanyProfile.objects.all().delete()

        response = self.post([self.row()])

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("has not been set up yet", response.data["error"])


# Scan time checks (Assign Rental)
class RentableCheckApiTests(RentalWorldMixin, WarehouseAPITestCase):

    def setUp(self):
        super().setUp()
        self.build_rental_world()

    def check(self, serial_number=None):
        params = {} if serial_number is None else {"serial_number": serial_number}
        return self.client.get(reverse("device-rental-check"), params)

    def test_rentable_device_returns_its_details(self):
        response = self.check(self.device.serial_number)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mv = self.device.batch.model_version
        self.assertEqual(response.data, {
            "serial_number": self.device.serial_number, "model": mv.model, "version": mv.version,
        })

    def test_missing_serial_number_returns_400(self):
        response = self.check()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "serial_number is required.")

    def test_unknown_device_returns_404(self):
        self.assertEqual(self.check("zzz").status_code, status.HTTP_404_NOT_FOUND)

    def test_client_owned_and_already_rented_devices_return_409_at_scan_time(self):
        self.assertEqual(self.check(self.owned_device.serial_number).status_code, status.HTTP_409_CONFLICT)

        make_rental(self.device, self.customer)
        self.assertEqual(self.check(self.device.serial_number).status_code, status.HTTP_409_CONFLICT)

    def test_company_not_set_returns_409(self):
        CompanyProfile.objects.all().delete()

        self.assertEqual(self.check(self.device.serial_number).status_code, status.HTTP_409_CONFLICT)


# Scan time lookup (End Rental)
class ActiveRentalApiTests(RentalWorldMixin, WarehouseAPITestCase):

    def setUp(self):
        super().setUp()
        self.build_rental_world()

    def lookup(self, serial_number=None):
        params = {} if serial_number is None else {"serial_number": serial_number}
        return self.client.get(reverse("device-rental-active"), params)

    def test_returns_the_active_rental_details(self):
        rental = make_rental(self.device, self.customer)

        response = self.lookup(self.device.serial_number)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["rental_id"], rental.pk)
        self.assertEqual(response.data["serial_number"], self.device.serial_number)
        self.assertEqual(response.data["client"], "customer")

    def test_device_not_on_rent_returns_404(self):
        response = self.lookup(self.device.serial_number)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "This device is not currently on rent.")

    def test_ended_rental_is_not_returned(self):
        make_rental(self.device, self.customer, returned_at=timezone.localdate())

        self.assertEqual(self.lookup(self.device.serial_number).status_code, status.HTTP_404_NOT_FOUND)

    def test_missing_serial_number_returns_400(self):
        self.assertEqual(self.lookup().status_code, status.HTTP_400_BAD_REQUEST)


# End rentals: one endpoint for one or many
class EndRentalApiTests(RentalWorldMixin, WarehouseAPITestCase):

    def setUp(self):
        super().setUp()
        self.build_rental_world()
        self.rental = make_rental(self.device, self.customer)
        self.today = timezone.localdate().isoformat()

    def end_many(self, **body):
        return self.client.post(reverse("device-rental-end-bulk"), body, format="json")

    def end_one(self, rental_id=None, **body):
        """Ending one rental is the bulk endpoint with a single id."""
        if rental_id is not None:
            body["rental_ids"] = [rental_id]
        return self.end_many(**body)

    # one

    def test_ends_one_rental(self):
        response = self.end_one(rental_id=self.rental.pk, end_date=self.today)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], f"Rental ended for {self.device.serial_number}.")
        self.assertEqual(response.data["rentals"][0]["returned_at"], self.today)
        self.rental.refresh_from_db()
        self.assertFalse(self.rental.is_active)

    def test_unknown_rental_returns_409(self):
        response = self.end_one(rental_id=999999, end_date=self.today)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "Rental 999999 does not exist.")

    def test_missing_or_invalid_end_date_returns_400(self):
        self.assertEqual(self.end_one(rental_id=self.rental.pk).data["error"], "Choose an end date.")
        self.assertEqual(
            self.end_one(rental_id=self.rental.pk, end_date="31/12/2026").data["error"],
            "The end date must be a valid date (YYYY-MM-DD).",
        )

    def test_future_end_date_returns_409(self):
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()

        response = self.end_one(rental_id=self.rental.pk, end_date=tomorrow)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("End date cannot be in the future.", response.data["error"])

    def test_ending_twice_returns_409(self):
        self.end_one(rental_id=self.rental.pk, end_date=self.today)

        response = self.end_one(rental_id=self.rental.pk, end_date=self.today)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("This rental has already been ended.", response.data["error"])

    # many

    def test_ends_many_rentals_with_one_date(self):
        other = make_rental(make_device(batch=self.device.batch), self.customer)

        response = self.end_many(rental_ids=[self.rental.pk, other.pk], end_date=self.today)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "2 rentals ended.")
        self.assertEqual(len(response.data["rentals"]), 2)
        self.assertEqual(DeviceRental.objects.filter(returned_at__isnull=True).count(), 0)

    def test_repeated_ids_are_collapsed_not_rejected(self):
        response = self.end_many(rental_ids=[self.rental.pk, self.rental.pk], end_date=self.today)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], f"Rental ended for {self.rental.device.serial_number}.")

    def test_bulk_validation_errors_return_400(self):
        cases = [
            ({"rental_ids": [], "end_date": self.today}, "Scan at least one device."),
            ({"end_date": self.today}, "Scan at least one device."),
            ({"rental_ids": [0], "end_date": self.today}, "Invalid rental id."),
            ({"rental_ids": ["abc"], "end_date": self.today}, "Invalid rental id."),
            ({"rental_ids": [1] * 51, "end_date": self.today}, "A batch can hold at most 50 devices."),
            ({"rental_ids": [self.rental.pk]}, "Choose an end date."),
        ]
        for body, message in cases:
            with self.subTest(message=message, body=str(body)[:40]):
                response = self.end_many(**body)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data["error"], message)

    def test_unknown_rental_in_a_bulk_end_returns_409(self):
        response = self.end_many(rental_ids=[self.rental.pk, 999999], end_date=self.today)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "Rental 999999 does not exist.")

    def test_one_already_ended_rental_blocks_the_whole_bulk_end(self):
        done = make_rental(make_device(batch=self.device.batch), self.customer, returned_at=timezone.localdate())

        response = self.end_many(rental_ids=[self.rental.pk, done.pk], end_date=self.today)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn(done.device.serial_number, response.data["error"])
        self.rental.refresh_from_db()
        self.assertTrue(self.rental.is_active)  # all or nothing


# Company (set once)
class CompanyApiTests(WarehouseAPITestCase):

    def get(self):
        return self.client.get(reverse("company"))

    def post(self, **body):
        return self.client.post(reverse("company"), body, format="json")

    def test_reports_not_set_until_a_company_is_chosen(self):
        response = self.get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {"is_set": False, "client": None})

    def test_sets_the_company_once(self):
        acme = make_client("acme")

        response = self.post(client=acme.id)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "acme is now set as the company.")
        self.assertEqual(response.data["client"], {"id": acme.id, "client_name": "acme"})
        self.assertEqual(CompanyProfile.objects.get().set_by, self.user)
        self.assertEqual(self.get().data, {"is_set": True, "client": {"id": acme.id, "client_name": "acme"}})

    def test_company_cannot_be_changed_afterwards(self):
        first, second = make_client("first"), make_client("second")
        self.post(client=first.id)

        response = self.post(client=second.id)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "The company has already been set and can't be changed.")
        self.assertEqual(CompanyProfile.objects.get().client, first)

    def test_missing_or_unknown_client_returns_400(self):
        self.assertEqual(self.post().data["error"], "Select a client.")
        self.assertEqual(self.post(client=999999).data["error"], "Selected client does not exist.")
        self.assertEqual(CompanyProfile.objects.count(), 0)


# Permissions: every rental / company endpoint is Warehouse only
class RentalPermissionApiTests(RentalWorldMixin, WarehouseAPITestCase):

    ENDPOINTS = [
        ("get", "device-rental-check"),
        ("get", "device-rental-active"),
        ("post", "device-rental-create"),
        ("post", "device-rental-end-bulk"),
        ("get", "company"),
        ("post", "company"),
    ]

    def setUp(self):
        super().setUp()
        self.build_rental_world()

    def call(self, method, name):
        return getattr(self.client, method)(reverse(name), {}, format="json") if method == "post" \
            else self.client.get(reverse(name))

    def test_anonymous_users_are_rejected_everywhere(self):
        self.authenticate_as(None)
        for method, name in self.ENDPOINTS:
            with self.subTest(endpoint=f"{method} {name}"):
                self.assertEqual(self.call(method, name).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_other_departments_are_forbidden_everywhere(self):
        self.authenticate_as(make_user(department=OTHER_DEPARTMENT))
        for method, name in self.ENDPOINTS:
            with self.subTest(endpoint=f"{method} {name}"):
                self.assertEqual(self.call(method, name).status_code, status.HTTP_403_FORBIDDEN)