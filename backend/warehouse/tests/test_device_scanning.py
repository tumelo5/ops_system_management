"""
Device scanning, tested one layer at a time.

  Serializer : trims + lowercases, rejects bad input        (SimpleTestCase, no DB)
  Service    : matches the SN to a batch by prefix, saves   (TestCase)
  API        : permissions, status codes, response shape    (APITestCase)

The service expects already normalised input (the serializer's job), so service tests
pass lowercase SNs and the normalisation is proven at the serializer and API layers.
"""
from django.db import transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework import status

from ..models import Batch, Device
from ..serializers import DeviceScanSerializer
from ..services import DeviceService
from .base import WarehouseAPITestCase
from .factories import OTHER_DEPARTMENT, make_batch, make_user

                                                                           
# Serializer layer                                                                           
class DeviceScanSerializerTests(SimpleTestCase):

    def errors_for(self, data):
        serializer = DeviceScanSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        return [str(e) for e in serializer.errors["serial_number"]]

    def test_serial_number_is_trimmed_and_lowercased(self):
        serializer = DeviceScanSerializer(data={"serial_number": "  ABC00123  "})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["serial_number"], "abc00123")

    def test_serial_number_of_exactly_100_characters_is_accepted(self):
        self.assertTrue(DeviceScanSerializer(data={"serial_number": "a" * 100}).is_valid())

    def test_serial_number_over_100_characters_is_rejected(self):
        self.assertEqual(
            self.errors_for({"serial_number": "a" * 101}),
            ["Serial number must be 100 characters or fewer."],
        )

    def test_missing_serial_number_is_rejected(self):
        self.assertEqual(self.errors_for({}), ["Serial number is required."])

    def test_null_serial_number_is_rejected(self):
        self.assertEqual(self.errors_for({"serial_number": None}), ["Serial number is required."])

    def test_empty_serial_number_is_rejected(self):
        self.assertEqual(self.errors_for({"serial_number": ""}), ["Serial number is required."])

    def test_whitespace_only_serial_number_is_rejected(self):
        self.assertEqual(self.errors_for({"serial_number": "   "}), ["Serial number is required."])

                                                                          
# Service layer                                                                     
class DeviceServiceScanTests(TestCase):

    def setUp(self):
        self.batch = make_batch(batch_code="abc")

    #the happy path    

    def test_valid_scan_saves_device_under_the_matching_batch(self):
        result = DeviceService.scan_device("abc00001")

        self.assertIsNone(result)  # scan_device returns nothing; the view builds the response
        device = Device.objects.get(serial_number="abc00001")
        self.assertEqual(device.batch, self.batch)
        self.assertEqual(device.device_status, "ACTIVE")
        self.assertIsNotNone(device.created_at)
        self.assertEqual(Batch.objects.count(), 1)  # scanning never creates batches

    def test_scan_uses_the_batch_whose_code_starts_the_sn(self):
        other = make_batch(batch_code="xyz")

        DeviceService.scan_device("xyz00001")

        self.assertEqual(Device.objects.get(serial_number="xyz00001").batch, other)

    #no match    

    def test_scan_rejects_sn_that_matches_no_batch(self):
        with self.assertRaisesMessage(ValueError, "No batch matches serial number 'zzz00001'"):
            DeviceService.scan_device("zzz00001")
        self.assertEqual(Device.objects.count(), 0)

    def test_batch_code_must_be_at_the_start_of_the_sn_not_inside_it(self):
        with self.assertRaises(ValueError):
            DeviceService.scan_device("00abc001")
        self.assertEqual(Device.objects.count(), 0)

    def test_sn_shorter_than_the_batch_code_is_rejected(self):
        with self.assertRaises(ValueError):
            DeviceService.scan_device("ab")
        self.assertEqual(Device.objects.count(), 0)

    def test_batch_with_an_empty_code_never_matches(self):
        make_batch(batch_code="")  # an empty prefix would otherwise match every SN

        with self.assertRaises(ValueError):
            DeviceService.scan_device("zzz00001")
        # and it does not make a good SN ambiguous either
        DeviceService.scan_device("abc00001")
        self.assertTrue(Device.objects.filter(serial_number="abc00001").exists())

    #ambiguity (strict: more than one match is rejected)    

    def test_scan_rejects_sn_matching_more_than_one_batch(self):
        make_batch(batch_code="abcd")  # "abc" and "abcd" both start "abcd0001"

        with self.assertRaisesMessage(ValueError, "more than one batch code"):
            DeviceService.scan_device("abcd0001")
        self.assertEqual(Device.objects.count(), 0)

    def test_overlapping_codes_are_fine_when_the_sn_matches_only_one(self):
        make_batch(batch_code="abcd")

        DeviceService.scan_device("abc00001")  # "abcd" is not a prefix of this SN

        self.assertEqual(Device.objects.get(serial_number="abc00001").batch, self.batch)

    #duplicates    

    def test_duplicate_serial_number_is_rejected(self):
        DeviceService.scan_device("abc00001")

        with self.assertRaisesMessage(ValueError, "already exists"):
            DeviceService.scan_device("abc00001")
        self.assertEqual(Device.objects.count(), 1)

    def test_rejected_duplicate_does_not_poison_the_surrounding_transaction(self):
        # The savepoint lesson: without the inner atomic(), the IntegrityError would break
        # the outer transaction and the next query would raise TransactionManagementError.
        with transaction.atomic():
            DeviceService.scan_device("abc00001")
            with self.assertRaises(ValueError):
                DeviceService.scan_device("abc00001")
            DeviceService.scan_device("abc00002")

        self.assertEqual(Device.objects.count(), 2)

                                                                           
# API layer                                                                        
class ScanDeviceApiTests(WarehouseAPITestCase):

    url = reverse("devices scan")  # ASSUMPTION: no URL namespace; use "warehouse:devices scan" if there is one

    def setUp(self):
        super().setUp()
        self.batch = make_batch(batch_code="abc")

    def scan(self, serial_number, url=None):
        return self.client.post(url or self.url, {"serial_number": serial_number}, format="json")

    #success    

    def test_successful_scan_returns_201_and_saves_the_device(self):
        response = self.scan("abc00001")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["serial_number"], "abc00001")
        self.assertEqual(response.data["message"], "Device abc00001 scanned successfully.")
        self.assertEqual(Device.objects.get(serial_number="abc00001").batch, self.batch)

    def test_scan_normalises_case_and_whitespace_end_to_end(self):
        response = self.scan("  ABC00002  ")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["serial_number"], "abc00002")
        self.assertTrue(Device.objects.filter(serial_number="abc00002").exists())

    def test_legacy_devices_url_is_the_same_endpoint(self):
        for index, name in enumerate(["devices", "devices scan"], start=1):
            with self.subTest(url_name=name):
                response = self.scan(f"abc0010{index}", url=reverse(name))
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    #bad input (400)    

    def test_missing_serial_number_returns_400(self):
        response = self.client.post(self.url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Serial number is required.")

    def test_blank_serial_number_returns_400(self):
        response = self.scan("   ")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Serial number is required.")

    def test_over_long_serial_number_returns_400(self):
        response = self.scan("a" * 101)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Serial number must be 100 characters or fewer.")

    #rule failures (409)    

    def test_sn_that_matches_no_batch_returns_409(self):
        response = self.scan("zzz00001")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("No batch matches", response.data["error"])
        self.assertEqual(Device.objects.count(), 0)

    def test_sn_matching_two_batches_returns_409(self):
        make_batch(batch_code="abcd")

        response = self.scan("abcd0001")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("more than one batch code", response.data["error"])
        self.assertEqual(Device.objects.count(), 0)

    def test_duplicate_scan_returns_409(self):
        self.assertEqual(self.scan("abc00001").status_code, status.HTTP_201_CREATED)

        response = self.scan("abc00001")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("already exists", response.data["error"])
        self.assertEqual(Device.objects.count(), 1)

    def test_error_is_always_a_plain_string(self):
        # The frontend renders response.data.error directly; an object would crash React.
        for sn in ["", "zzz00001", "a" * 101]:
            with self.subTest(sn=sn[:10]):
                response = self.scan(sn)
                self.assertIsInstance(response.data["error"], str)

    #permissions    

    def test_anonymous_user_is_rejected(self):
        self.authenticate_as(None)

        response = self.scan("abc00001")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Device.objects.count(), 0)

    def test_other_departments_are_forbidden(self):
        self.authenticate_as(make_user(department=OTHER_DEPARTMENT))

        response = self.scan("abc00001")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Device.objects.count(), 0)