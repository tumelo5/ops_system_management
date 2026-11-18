"""
Correct Info tab: client, model, version and batch-code typo corrections.

Corrections are applied in place (no history table). Client / model / version have no
"in use" lock; a batch code can only be corrected while no device exists under it.
BatchCorrection (legacy, to be deleted) is deliberately not tested.
"""
from django.urls import reverse
from rest_framework import status

from ..models import Batch, Client, DeviceModelVersion
from .base import WarehouseAPITestCase
from .factories import OTHER_DEPARTMENT, make_batch, make_client, make_device, make_model_version, make_user


class ClientCorrectionApiTests(WarehouseAPITestCase):

    def patch(self, client_id, name):
        return self.client.patch(reverse("client-correction", args=[client_id]), {"client_name": name}, format="json")

    def test_corrects_the_name_in_place_and_records_who_and_when(self):
        acme = make_client("acmee")

        response = self.patch(acme.id, "  ACME ")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Client corrected.")
        acme.refresh_from_db()
        self.assertEqual(acme.client_name, "acme")
        self.assertEqual(acme.correction_count, 1)
        self.assertEqual(acme.last_corrected_by, self.user)
        self.assertIsNotNone(acme.last_corrected_at)
        self.assertEqual(Client.objects.count(), 1)  # corrected, not duplicated

    def test_each_correction_increments_the_counter(self):
        acme = make_client("a")
        self.patch(acme.id, "b")
        self.patch(acme.id, "c")

        acme.refresh_from_db()
        self.assertEqual((acme.client_name, acme.correction_count), ("c", 2))

    def test_name_that_belongs_to_another_client_returns_409(self):
        make_client("beta")
        alpha = make_client("alpha")

        response = self.patch(alpha.id, "BETA")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "That value already exists.")
        alpha.refresh_from_db()
        self.assertEqual((alpha.client_name, alpha.correction_count), ("alpha", 0))

    def test_unknown_client_returns_404(self):
        response = self.patch(999999, "x")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Client not found.")

    def test_blank_name_returns_400(self):
        response = self.patch(make_client("a").id, "  ")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Client name is required.")

    def test_other_departments_are_forbidden(self):
        acme = make_client("acme")
        self.authenticate_as(make_user(department=OTHER_DEPARTMENT))

        self.assertEqual(self.patch(acme.id, "x").status_code, status.HTTP_403_FORBIDDEN)


class ModelCorrectionApiTests(WarehouseAPITestCase):

    def patch(self, model, new_model):
        return self.client.patch(reverse("model-correction"), {"model": model, "new_model": new_model}, format="json")

    def test_rename_applies_to_every_version_of_the_model(self):
        v1 = make_model_version(model="pos1", version="v1")
        v2 = make_model_version(model="pos1", version="v2")
        other = make_model_version(model="keep", version="v1")

        response = self.patch(" POS1 ", "POS-One")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for row in (v1, v2):
            row.refresh_from_db()
            self.assertEqual((row.model, row.correction_count, row.last_corrected_by), ("pos-one", 1, self.user))
        other.refresh_from_db()
        self.assertEqual((other.model, other.correction_count), ("keep", 0))

    def test_unknown_model_returns_404(self):
        response = self.patch("nope", "x")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Model not found.")

    def test_new_name_that_already_exists_returns_409_and_changes_nothing(self):
        make_model_version(model="pos1", version="v1")
        make_model_version(model="pos2", version="v1")

        response = self.patch("pos1", "POS2")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "A model named 'pos2' already exists.")
        self.assertTrue(DeviceModelVersion.objects.filter(model="pos1").exists())

    def test_missing_fields_return_400(self):
        response = self.client.patch(reverse("model-correction"), {"model": "pos1"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Select a model and enter the corrected name.")


class VersionCorrectionApiTests(WarehouseAPITestCase):

    def patch(self, version_id, version):
        return self.client.patch(reverse("version-correction", args=[version_id]), {"version": version}, format="json")

    def test_corrects_the_version_in_place(self):
        row = make_model_version(model="pos1", version="v1x")

        response = self.patch(row.id, " V1 ")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        row.refresh_from_db()
        self.assertEqual((row.version, row.correction_count, row.last_corrected_by), ("v1", 1, self.user))

    def test_version_that_already_exists_for_the_same_model_returns_409(self):
        make_model_version(model="pos1", version="v2")
        row = make_model_version(model="pos1", version="v1")

        response = self.patch(row.id, "V2")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "That value already exists.")

    def test_same_version_string_is_fine_under_a_different_model(self):
        make_model_version(model="other", version="v2")
        row = make_model_version(model="pos1", version="v1")

        self.assertEqual(self.patch(row.id, "v2").status_code, status.HTTP_200_OK)

    def test_unknown_version_returns_404(self):
        response = self.patch(999999, "v1")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Version not found.")


class BatchCodeCorrectionApiTests(WarehouseAPITestCase):

    def setUp(self):
        super().setUp()
        self.batch = make_batch(batch_code="b0oo1")  # typo: letters o instead of zeros

    def patch(self, batch_id, code):
        return self.client.patch(reverse("batch-code-correction", args=[batch_id]), {"batch_code": code}, format="json")

    # --- lookup ---

    def lookup(self, code):
        return self.client.get(reverse("batch-code-lookup"), {"batch_code": code})

    def test_lookup_finds_the_batch_normalising_the_code(self):
        response = self.lookup("  B0OO1 ")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.batch.id)
        self.assertEqual(response.data["client_name"], self.batch.client.client_name)
        self.assertTrue(response.data["correctable"])

    def test_lookup_reports_not_correctable_once_a_device_exists(self):
        make_device(batch=self.batch)

        self.assertFalse(self.lookup("b0oo1").data["correctable"])

    def test_lookup_unknown_code_returns_404_and_missing_code_returns_400(self):
        self.assertEqual(self.lookup("nope").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.lookup("").status_code, status.HTTP_400_BAD_REQUEST)

    # --- correction ---

    def test_corrects_the_code_in_place_and_tracks_the_correction(self):
        response = self.patch(self.batch.id, " B0001 ")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Batch code corrected.")
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.batch_code, "b0001")
        self.assertEqual(self.batch.correction_count, 1)
        self.assertIsNotNone(self.batch.corrected_at)
        self.assertEqual(Batch.objects.count(), 1)

    def test_same_code_is_refused(self):
        response = self.patch(self.batch.id, "B0OO1")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "The new batch code is the same as the current one.")

    def test_code_is_locked_once_a_device_was_scanned_under_it(self):
        make_device(batch=self.batch)

        response = self.patch(self.batch.id, "b0001")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("can't be corrected", response.data["error"])
        self.batch.refresh_from_db()
        self.assertEqual((self.batch.batch_code, self.batch.correction_count), ("b0oo1", 0))

    def test_code_that_belongs_to_another_batch_is_refused(self):
        make_batch(batch_code="b0001")

        response = self.patch(self.batch.id, "B0001")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"], "Batch code 'b0001' already exists.")

    def test_unknown_batch_returns_404(self):
        response = self.patch(999999, "x")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Batch not found.")

    def test_blank_code_returns_400(self):
        response = self.patch(self.batch.id, "  ")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Batch code is required.")

    def test_other_departments_are_forbidden(self):
        self.authenticate_as(make_user(department=OTHER_DEPARTMENT))
        self.assertEqual(self.patch(self.batch.id, "b0001").status_code, status.HTTP_403_FORBIDDEN)