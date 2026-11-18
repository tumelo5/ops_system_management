"""
Add Clients (step 1): bulk creation of base client records.

  Serializer : normalisation, duplicates, row cap, empty list
  Service    : all  or  nothing creation
  API        : status codes, permissions, error contract

The two gaps found earlier (no serverside row cap, empty list returning 201) are now
closed by ClientListSerializer, so they are asserted here as rejections.
"""
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from ..models import Client
from ..serializers import MAX_CLIENT_ROWS, ClientSerializer
from ..services import ClientService
from .base import WarehouseAPITestCase
from .factories import OTHER_DEPARTMENT, make_client, make_user


                                                                                                                                                      
# Serializer layer                                                                                                                                                    
class ClientSerializerTests(TestCase):

    def run_serializer(self, rows):
        serializer = ClientSerializer(data=rows, many=True)
        return serializer, serializer.is_valid()

    def names(self, *names):
        return [{"client_name": n} for n in names]

    def test_names_are_trimmed_and_lowercased(self):
        serializer, valid = self.run_serializer(self.names("  ACME Ltd  "))

        self.assertTrue(valid)
        self.assertEqual(serializer.validated_data[0]["client_name"], "acme ltd")

    def test_name_that_exists_in_the_database_is_rejected_ignoring_case(self):
        make_client("acme")

        serializer, valid = self.run_serializer(self.names("ACME"))

        self.assertFalse(valid)
        self.assertEqual(str(serializer.errors[0]["client_name"][0]), "Client 'ACME' already exists.")

    def test_same_name_twice_in_one_payload_is_rejected_after_normalising(self):
        serializer, valid = self.run_serializer(self.names(" Acme", "acme "))

        self.assertFalse(valid)
        self.assertEqual(
            str(serializer.errors["non_field_errors"][0]),
            "Client 'acme' appears more than once.",
        )

    def test_exactly_the_row_cap_is_accepted(self):
        _, valid = self.run_serializer(self.names(*[f"c{i}" for i in range(MAX_CLIENT_ROWS)]))
        self.assertTrue(valid)

    def test_more_than_the_row_cap_is_rejected(self):
        serializer, valid = self.run_serializer(self.names(*[f"c{i}" for i in range(MAX_CLIENT_ROWS + 1)]))

        self.assertFalse(valid)
        self.assertEqual(
            str(serializer.errors["non_field_errors"][0]),
            f"At most {MAX_CLIENT_ROWS} rows can be submitted at once.",
        )

    def test_empty_list_is_rejected(self):
        serializer, valid = self.run_serializer([])

        self.assertFalse(valid)
        self.assertEqual(str(serializer.errors["non_field_errors"][0]), "Add at least one row.")

    def test_missing_name_is_rejected(self):
        serializer, valid = self.run_serializer([{}])

        self.assertFalse(valid)
        self.assertEqual(str(serializer.errors[0]["client_name"][0]), "Client name is required.")

    def test_blank_and_whitespace_names_are_rejected(self):
        for value in ["", "   "]:
            with self.subTest(value=repr(value)):
                serializer, valid = self.run_serializer(self.names(value))
                self.assertFalse(valid)
                self.assertEqual(str(serializer.errors[0]["client_name"][0]), "Client name is required.")

    def test_name_over_255_characters_is_rejected(self):
        serializer, valid = self.run_serializer(self.names("a" * 256))

        self.assertFalse(valid)
        self.assertEqual(
            str(serializer.errors[0]["client_name"][0]),
            "Client name must be 255 characters or fewer.",
        )

    def test_errors_point_at_the_row_that_failed(self):
        make_client("taken")

        serializer, valid = self.run_serializer(self.names("fresh", "taken"))

        self.assertFalse(valid)
        self.assertEqual(serializer.errors[0], {})  # row 0 passed
        self.assertIn("client_name", serializer.errors[1])  # row 1 failed


                                                                                                                                                   
# Service layer                                                                                                                                                
class CreateBulkBaseServiceTests(TestCase):

    def test_creates_every_client_in_order(self):
        created = ClientService.create_bulk_base([{"client_name": "a"}, {"client_name": "b"}])

        self.assertEqual([c.client_name for c in created], ["a", "b"])
        self.assertEqual(Client.objects.count(), 2)

    def test_new_clients_start_active_with_no_corrections(self):
        (client,) = ClientService.create_bulk_base([{"client_name": "a"}])

        self.assertEqual(client.client_status, "Active")
        self.assertEqual(client.correction_count, 0)

    def test_duplicate_in_the_middle_rolls_back_the_whole_batch(self):
        rows = [{"client_name": "a"}, {"client_name": "b"}, {"client_name": "a"}]

        with self.assertRaisesMessage(ValueError, "Client 'a' already exists."):
            ClientService.create_bulk_base(rows)

        self.assertEqual(Client.objects.count(), 0)

    def test_client_that_already_exists_is_rejected_and_nothing_is_added(self):
        make_client("a")

        with self.assertRaisesMessage(ValueError, "already exists"):
            ClientService.create_bulk_base([{"client_name": "b"}, {"client_name": "a"}])

        self.assertEqual(list(Client.objects.values_list("client_name", flat=True)), ["a"])


                                                                                                                                                      
# API layer                                                                                                                                                     
class BulkClientsApiTests(WarehouseAPITestCase):

    def post(self, *names):
        return self.client.post(
            reverse("clients  bulk  base"),
            {"clients": [{"client_name": n} for n in names]},
            format="json",
        )

    def test_creates_clients_and_returns_201(self):
        response = self.post("Acme", "Beta")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "2 clients created successfully.")
        self.assertEqual(
            sorted(Client.objects.values_list("client_name", flat=True)),
            ["acme", "beta"],
        )

    def test_five_clients_are_accepted(self):
        self.assertEqual(self.post(*[f"c{i}" for i in range(5)]).status_code, status.HTTP_201_CREATED)

    def test_six_clients_are_rejected_with_400(self):
        response = self.post(*[f"c{i}" for i in range(6)])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "At most 5 rows can be submitted at once.")
        self.assertEqual(Client.objects.count(), 0)

    def test_empty_list_is_rejected_with_400(self):
        response = self.post()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Add at least one row.")

    def test_missing_clients_key_is_rejected_with_400(self):
        response = self.client.post(reverse("clients  bulk  base"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Add at least one row.")

    def test_name_that_already_exists_returns_400_and_creates_nothing(self):
        make_client("acme")

        response = self.post("fresh", "ACME")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Client 'ACME' already exists.")
        self.assertEqual(Client.objects.count(), 1)

    def test_duplicate_names_in_the_payload_return_400(self):
        response = self.post("acme", " ACME ")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Client 'acme' appears more than once.")
        self.assertEqual(Client.objects.count(), 0)

    def test_blank_name_returns_400(self):
        response = self.post("   ")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Client name is required.")

    def test_race_lost_at_the_service_returns_409(self):
        # The serializer check passed but the DB constraint fired anyway (two requests racing).
        with patch.object(ClientService, "create_bulk_base", side_effect=ValueError("Client 'x' already exists.")):
            response = self.post("x")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "Client 'x' already exists.")

    def test_unexpected_failure_returns_a_generic_500(self):
        with patch.object(ClientService, "create_bulk_base", side_effect=RuntimeError("boom")):
            response = self.post("x")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data["error"], "Failed to create clients.")  # no internal detail leaked

    def test_anonymous_user_is_rejected(self):
        self.authenticate_as(None)
        self.assertEqual(self.post("acme").status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Client.objects.count(), 0)

    def test_other_departments_are_forbidden(self):
        self.authenticate_as(make_user(department=OTHER_DEPARTMENT))
        self.assertEqual(self.post("acme").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Client.objects.count(), 0)