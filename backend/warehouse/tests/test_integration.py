"""
Integration stories: real multi step workflows through the real stack (HTTP  > serializer  >
service  > DB), nothing mocked. Each test is one story across several features.

Rule detail is proven in the per layer files; these only prove the features fit together.
"""
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from ..models import Batch, Client, Device, DeviceRental
from ..services import DeviceRentalService
from .base import WarehouseAPITestCase
from .factories import OTHER_DEPARTMENT, make_user


class WarehouseWorkflowTests(WarehouseAPITestCase):

    #small API helpers: one per user action    

    def api(self, method, name, data=None, args=None):
        url = reverse(name, args=args)
        if method == "get":
            return self.client.get(url, data or {})
        return getattr(self.client, method)(url, data if data is not None else {}, format="json")

    def create_clients(self, *names):
        response = self.api("post", "clients bulk base", {"clients": [{"client_name": n} for n in names]})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        return [Client.objects.get(client_name=n.strip().lower()) for n in names]

    def set_company(self, client):
        response = self.api("post", "company", {"client": client.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def link(self, client, batch_code, model="pos1", version="v1"):
        response = self.api("post", "clients bulk links", {"links": [
            {"client": client.id, "batch_code": batch_code, "model": model, "version": version}
        ]})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)

    def scan(self, serial_number):
        return self.api("post", "devices scan", {"serial_number": serial_number})

    def rent(self, serial_numbers, client):
        return self.api("post", "device rental create", [
            {"device": sn, "rental_client": client.id} for sn in serial_numbers
        ])
                                                               

    def test_story_intake_to_rental_and_back(self):
        """Create clients  > link  > scan  > rent  > client resolves to renter  > end  > back to owner."""
        company, customer = self.create_clients("JohnDoe", "Customer")
        self.set_company(company)
        self.link(company, "CMP01")

        # scanning is normalised and lands under the company's batch
        self.assertEqual(self.scan("  CMP0100001 ").status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.scan("cmp0100002").status_code, status.HTTP_201_CREATED)
        device = Device.objects.get(serial_number="cmp0100001")
        self.assertEqual(device.batch.client, company)

        # scan time check passes, then the rental is created
        ok = self.api("get", "device rental check", {"serial_number": "cmp0100001"})
        self.assertEqual(ok.status_code, status.HTTP_200_OK)
        self.assertEqual(self.rent(["cmp0100001", "cmp0100002"], customer).status_code, status.HTTP_201_CREATED)

        # a rented device now fails the scan time check ...
        again = self.api("get", "device rental check", {"serial_number": "cmp0100001"})
        self.assertEqual(again.status_code, status.HTTP_409_CONFLICT)

        # ... and every department resolves its client to the renter
        self.assertEqual(DeviceRentalService.resolve_operational_client("cmp0100001"), (customer, "RENTAL"))

        # end one rental from the scan screen
        active = self.api("get", "device rental active", {"serial_number": "cmp0100001"})
        self.assertEqual(active.status_code, status.HTTP_200_OK)
        ended = self.api("post", "device rental end", {
            "rental_id": active.data["rental_id"], "end_date": timezone.localdate().isoformat(),
        })
        self.assertEqual(ended.status_code, status.HTTP_200_OK)

        # ownership resolution falls back to the permanent owner; the other device is still rented
        self.assertEqual(DeviceRentalService.resolve_operational_client("cmp0100001"), (company, "BATCH"))
        self.assertEqual(DeviceRentalService.resolve_operational_client("cmp0100002"), (customer, "RENTAL"))

        # the permanent Device  > Batch  > Client link never moved, and history is kept
        device.refresh_from_db()
        self.assertEqual(device.batch.client, company)
        self.assertEqual(DeviceRental.objects.count(), 2)

    def test_story_client_owned_devices_can_never_be_rented(self):
        """A wrong SN from Finance (a client owned device) is blocked at scan time AND at submit time."""
        company, customer, other = self.create_clients("JohnDoe", "Customer", "Other")
        self.set_company(company)
        self.link(customer, "CUS01")
        self.scan("cus0100001")

        check = self.api("get", "device rental check", {"serial_number": "cus0100001"})
        self.assertEqual(check.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(self.rent(["cus0100001"], other).status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(DeviceRental.objects.count(), 0)
        self.assertEqual(
            DeviceRentalService.resolve_operational_client("cus0100001"), (customer, "BATCH")
        )

    def test_story_a_failed_bulk_step_leaves_earlier_work_untouched(self):
        """Rent two devices, end one, then a bulk end that includes the ended one must change nothing."""
        company, customer = self.create_clients("JohnDoe", "Customer")
        self.set_company(company)
        self.link(company, "CMP01")
        self.scan("cmp0100001")
        self.scan("cmp0100002")
        self.rent(["cmp0100001", "cmp0100002"], customer)

        first, second = (DeviceRental.objects.get(device__serial_number=sn) for sn in ["cmp0100001", "cmp0100002"])
        today = timezone.localdate().isoformat()
        self.api("post", "device rental end", {"rental_id": first.pk, "end_date": today})

        response = self.api("post", "device rental end bulk", {"rental_ids": [second.pk, first.pk], "end_date": today})

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        second.refresh_from_db()
        self.assertTrue(second.is_active)  # untouched by the failed batch

    def test_story_batch_code_typo_is_fixable_only_until_devices_exist(self):
        """Correct a mistyped batch code, scan under the corrected code, then the code locks."""
        (acme,) = self.create_clients("Acme")
        self.link(acme, "B0OO1")  # typo
        batch = Batch.objects.get()

        # nothing scanned yet  > correctable
        fix = self.api("patch", "batch code correction", {"batch_code": "B0001"}, args=[batch.id])
        self.assertEqual(fix.status_code, status.HTTP_200_OK, fix.data)

        # the old code no longer matches anything; the corrected one does
        self.assertEqual(self.scan("b0oo100001").status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(self.scan("b000100001").status_code, status.HTTP_201_CREATED)

        # now a device exists under the code  > locked
        again = self.api("patch", "batch code correction", {"batch_code": "b9999"}, args=[batch.id])
        self.assertEqual(again.status_code, status.HTTP_409_CONFLICT)
        batch.refresh_from_db()
        self.assertEqual(batch.batch_code, "b0001")

    def test_story_existing_client_repeat_batch_scans_under_its_own_code(self):
        """First batch via Linking, repeat purchase via Existing Client, devices scan to the right batch."""
        (acme,) = self.create_clients("Acme")
        self.link(acme, "B001")
        repeat = self.api("post", "clients existing batch", {
            "client": acme.id, "batch_code": "B002", "model": "pos1", "version": "v1",
        })
        self.assertEqual(repeat.status_code, status.HTTP_201_CREATED, repeat.data)

        self.scan("b00100001")
        self.scan("b00200001")

        first, second = Batch.objects.get(batch_code="b001"), Batch.objects.get(batch_code="b002")
        self.assertEqual(first.model_version, second.model_version)  # one shared product row
        self.assertEqual(Device.objects.get(serial_number="b00100001").batch, first)
        self.assertEqual(Device.objects.get(serial_number="b00200001").batch, second)

    def test_story_other_departments_cannot_run_any_step_of_the_workflow(self):
        self.authenticate_as(make_user(department=OTHER_DEPARTMENT))

        for method, name, body in [
            ("post", "clients bulk base", {"clients": [{"client_name": "x"}]}),
            ("post", "clients bulk links", {"links": []}),
            ("post", "devices scan", {"serial_number": "x"}),
            ("post", "device rental create", []),
            ("post", "company", {}),
        ]:
            with self.subTest(step=name):
                self.assertEqual(self.api(method, name, body).status_code, status.HTTP_403_FORBIDDEN)

        self.assertEqual(Client.objects.count(), 0)