"""
Linking (step 2), Existing Client, and the dropdown lookups.

  Linking         : a client's FIRST batch, resolving model + version
  Existing Client : every batch after the first; repeat purchases allowed
  Lookups         : clients awaiting linking, models, versions

Model and version live in one table (DeviceModelVersion), so "resolve" means
get_or_create on (model, version): shared between clients, never duplicated.
"""
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from ..models import Batch, DeviceModelVersion
from ..services import ClientService
from .base import WarehouseAPITestCase
from .factories import OTHER_DEPARTMENT, make_batch, make_client, make_model_version, make_user

                                                                                                                                                                                                                                
# Service layer: Linking                                                                                                                                                                                                                                 
class CreateBulkLinksServiceTests(TestCase):

    def entry(self, client, batch_code="b0001", model="pos1", version="v1"):
        return {"client": client, "batch_code": batch_code, "model": model, "version": version}

    def test_creates_the_batch_and_the_model_version(self):
        acme = make_client("acme")

        (result,) = ClientService.create_bulk_links([self.entry(acme)])

        batch = result["batch"]
        self.assertEqual((batch.client, batch.batch_code), (acme, "b0001"))
        self.assertEqual((batch.model_version.model, batch.model_version.version), ("pos1", "v1"))
        self.assertEqual(result["model_version"], batch.model_version)

    def test_two_clients_linking_the_same_product_share_one_model_version_row(self):
        acme, beta = make_client("acme"), make_client("beta")

        ClientService.create_bulk_links([
            self.entry(acme, "b0001"),
            self.entry(beta, "b0002"),
        ])

        self.assertEqual(DeviceModelVersion.objects.filter(model="pos1", version="v1").count(), 1)
        self.assertEqual(Batch.objects.get(batch_code="b0001").model_version,
                         Batch.objects.get(batch_code="b0002").model_version)

    def test_client_that_already_has_a_batch_is_rejected(self):
        acme = make_client("acme")
        make_batch(batch_code="old1", client=acme)

        with self.assertRaisesMessage(ValueError, "already has a batch code"):
            ClientService.create_bulk_links([self.entry(acme)])

        self.assertEqual(Batch.objects.count(), 1)

    def test_batch_code_that_already_exists_is_rejected_and_leaves_no_orphan_version(self):
        make_batch(batch_code="b0001")
        versions_before = DeviceModelVersion.objects.count()

        with self.assertRaisesMessage(ValueError, "Batch code 'b0001' already exists."):
            ClientService.create_bulk_links([self.entry(make_client("acme"), "b0001", model="newmodel")])

        self.assertEqual(DeviceModelVersion.objects.count(), versions_before)

    def test_one_bad_row_rolls_back_the_whole_batch(self):
        acme = make_client("acme")

        # the same client twice: row 1 succeeds, row 2 finds the client already linked
        with self.assertRaises(ValueError):
            ClientService.create_bulk_links([self.entry(acme, "b0001"), self.entry(acme, "b0002")])

        self.assertEqual(Batch.objects.count(), 0)
        self.assertEqual(DeviceModelVersion.objects.count(), 0)

                                                                                                                                                                                                                                
# Service layer: Existing Client                                                                                                                                                                                                                                
class ExistingClientServiceTests(TestCase):

    def setUp(self):
        self.acme = make_client("acme")
        self.version = make_model_version(model="pos1", version="v1")
        self.first = make_batch(batch_code="b0001", client=self.acme, model_version=self.version)

    def test_new_product_for_an_existing_client_creates_batch_and_version(self):
        batch = ClientService.create_existing_client_batch(self.acme.id, "pos2", "v1", "b0002")

        self.assertEqual(batch.client, self.acme)
        self.assertEqual((batch.model_version.model, batch.model_version.version), ("pos2", "v1"))

    def test_repeat_purchase_of_the_same_product_is_allowed_and_reuses_the_version(self):
        batch = ClientService.create_existing_client_batch(self.acme.id, "pos1", "v1", "b0002")

        self.assertEqual(batch.model_version, self.version)
        self.assertEqual(DeviceModelVersion.objects.count(), 1)
        self.assertEqual(Batch.objects.filter(client=self.acme).count(), 2)

    def test_unknown_client_is_rejected(self):
        with self.assertRaisesMessage(ValueError, "Client with id '999999' does not exist."):
            ClientService.create_existing_client_batch(999999, "pos1", "v1", "b0002")

    def test_duplicate_batch_code_is_rejected_and_leaves_no_orphan_version(self):
        versions_before = DeviceModelVersion.objects.count()

        with self.assertRaisesMessage(ValueError, "Batch code 'b0001' already exists."):
            ClientService.create_existing_client_batch(self.acme.id, "brandnew", "v9", "b0001")

        self.assertEqual(DeviceModelVersion.objects.count(), versions_before)

    #get_client_batches_for_version          
    def test_lists_the_clients_batches_for_a_product_oldest_first(self):
        second = make_batch(batch_code="b0002", client=self.acme, model_version=self.version)
        make_batch(batch_code="b0003", client=self.acme, model_version=make_model_version())  # other product

        result = ClientService.get_client_batches_for_version(self.acme.id, self.version.id)

        self.assertEqual(result, [
            {"id": self.first.id, "batch_code": "b0001"},
            {"id": second.id, "batch_code": "b0002"},
        ])

    def test_empty_list_when_the_client_has_not_bought_the_product(self):
        other_version = make_model_version()
        self.assertEqual(ClientService.get_client_batches_for_version(self.acme.id, other_version.id), [])

    def test_batches_listing_rejects_unknown_client_or_version(self):
        with self.assertRaisesMessage(ValueError, "Client with id '999999' does not exist."):
            ClientService.get_client_batches_for_version(999999, self.version.id)
        with self.assertRaisesMessage(ValueError, "Selected model and version do not exist."):
            ClientService.get_client_batches_for_version(self.acme.id, 999999)

                                                                                                                                                                                                                               
# Service layer: lookups                                                                                                                                                                                                                                
class LookupServiceTests(TestCase):

    def test_clients_awaiting_linking_are_those_without_any_batch(self):
        linked = make_client("linked")
        make_batch(client=linked)
        waiting_b, waiting_a = make_client("bravo"), make_client("alpha")

        result = list(ClientService.get_clients_awaiting_linking())

        self.assertEqual(result, [
            {"id": waiting_a.id, "client_name": "alpha"},
            {"id": waiting_b.id, "client_name": "bravo"},
        ])

    def test_models_are_distinct_and_sorted(self):
        make_model_version(model="b", version="1")
        make_model_version(model="b", version="2")
        make_model_version(model="a", version="1")

        self.assertEqual(list(ClientService.get_device_models()), [{"model": "a"}, {"model": "b"}])

    def test_versions_are_only_those_of_the_requested_model_sorted(self):
        v2 = make_model_version(model="m", version="v2")
        v1 = make_model_version(model="m", version="v1")
        make_model_version(model="other", version="v9")

        self.assertEqual(list(ClientService.get_device_model_versions("m")), [
            {"id": v1.id, "version": "v1"},
            {"id": v2.id, "version": "v2"},
        ])

                                                                                                                                                                                                                                
# API layer: Linking                                                                                                                                                                                                                              
class LinkingApiTests(WarehouseAPITestCase):

    def setUp(self):
        super().setUp()
        self.acme = make_client("acme")

    def post(self, links):
        return self.client.post(reverse("clients   bulk   links"), {"links": links}, format="json")

    def link(self, client=None, batch_code="b0001", model="pos1", version="v1"):
        return {"client": (client or self.acme).id, "batch_code": batch_code, "model": model, "version": version}

    def test_links_client_batch_and_product_and_returns_201(self):
        response = self.post([self.link()])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "1 batch codes and versions created successfully.")
        batch = Batch.objects.get(batch_code="b0001")
        self.assertEqual((batch.client, batch.model_version.model, batch.model_version.version),
                         (self.acme, "pos1", "v1"))

    def test_batch_code_model_and_version_are_normalised(self):
        self.post([self.link(batch_code="  B0001 ", model="POS One", version=" V1 ")])

        batch = Batch.objects.get()
        self.assertEqual(batch.batch_code, "b0001")
        self.assertEqual((batch.model_version.model, batch.model_version.version), ("pos one", "v1"))

    def test_empty_or_missing_links_are_rejected_with_400(self):
        for response in [self.post([]), self.client.post(reverse("clients   bulk   links"), {}, format="json")]:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data["error"], "Add at least one row.")

    def test_same_batch_code_twice_in_the_payload_returns_400(self):
        beta = make_client("beta")

        response = self.post([self.link(batch_code="B1"), self.link(client=beta, batch_code=" b1 ")])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Batch code 'b1' appears more than once.")
        self.assertEqual(Batch.objects.count(), 0)

    def test_batch_code_that_already_exists_returns_400(self):
        make_batch(batch_code="b0001")

        response = self.post([self.link(batch_code="B0001")])

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Batch code 'B0001' already exists.")

    def test_missing_or_unknown_client_returns_400(self):
        missing = {"batch_code": "b1", "model": "m", "version": "v"}
        unknown = self.link(batch_code="b2") | {"client": 999999}

        self.assertEqual(self.post([missing]).data["error"], "Client is required for Batch linking.")
        self.assertEqual(self.post([unknown]).data["error"], "Selected client does not exist.")

    def test_missing_model_or_version_returns_400(self):
        no_model = {"client": self.acme.id, "batch_code": "b1", "version": "v"}
        no_version = {"client": self.acme.id, "batch_code": "b2", "model": "m"}

        self.assertEqual(self.post([no_model]).data["error"], "Device model is required.")
        self.assertEqual(self.post([no_version]).data["error"], "Model version is required.")

    def test_client_that_already_has_a_batch_returns_409_and_creates_nothing(self):
        make_batch(batch_code="old1", client=self.acme)

        response = self.post([self.link()])

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("already has a batch code", response.data["error"])
        self.assertEqual(Batch.objects.count(), 1)

    def test_same_client_twice_in_one_payload_returns_409_and_creates_nothing(self):
        response = self.post([self.link(batch_code="b1"), self.link(batch_code="b2")])

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(Batch.objects.count(), 0)

    def test_other_departments_are_forbidden(self):
        self.authenticate_as(make_user(department=OTHER_DEPARTMENT))
        self.assertEqual(self.post([self.link()]).status_code, status.HTTP_403_FORBIDDEN)

                                                                                                                                                                                                                                  
# API layer: Existing Client                                                                                                                                                                                                                        
class ExistingClientApiTests(WarehouseAPITestCase):

    def setUp(self):
        super().setUp()
        self.acme = make_client("acme")
        self.version = make_model_version(model="pos1", version="v1")
        make_batch(batch_code="b0001", client=self.acme, model_version=self.version)

    #           validate selection          

    def validate(self, client, version):
        return self.client.post(reverse("clients   existing   validate"), {"client": client, "version": version}, format="json")

    def test_validate_returns_the_clients_existing_batches_for_the_product(self):
        response = self.validate(self.acme.id, self.version.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([b["batch_code"] for b in response.data["batches"]], ["b0001"])

    def test_validate_returns_an_empty_list_for_a_product_the_client_has_not_bought(self):
        response = self.validate(self.acme.id, make_model_version().id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["batches"], [])

    def test_validate_rejects_missing_or_malformed_ids_with_400(self):
        missing = self.client.post(reverse("clients   existing   validate"), {}, format="json")
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing.data["error"], "client and version are required.")

        for bad in ["abc", 0,    1]:
            with self.subTest(value=bad):
                response = self.validate(bad, self.version.id)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data["error"], "client and version must be valid ids.")

    def test_validate_returns_404_for_unknown_client_or_version(self):
        self.assertEqual(self.validate(999999, self.version.id).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.validate(self.acme.id, 999999).status_code, status.HTTP_404_NOT_FOUND)

    #create batch          
    def create(self, **overrides):
        body = {"client": self.acme.id, "batch_code": "b0002", "model": "pos1", "version": "v1"} | overrides
        return self.client.post(reverse("clients   existing   batch"), body, format="json")

    def test_repeat_purchase_creates_a_new_batch_for_the_same_product(self):
        response = self.create()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Batch code 'b0002' created for pos1 v1.")
        self.assertEqual(Batch.objects.filter(client=self.acme).count(), 2)
        self.assertEqual(DeviceModelVersion.objects.count(), 1)

    def test_new_product_is_created_and_input_is_normalised(self):
        response = self.create(batch_code=" B0003 ", model="POS2", version=" V2 ")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        batch = Batch.objects.get(batch_code="b0003")
        self.assertEqual((batch.model_version.model, batch.model_version.version), ("pos2", "v2"))

    def test_existing_batch_code_returns_400(self):
        response = self.create(batch_code="B0001")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Batch code 'B0001' already exists.")

    def test_unknown_client_returns_400(self):
        response = self.create(client=999999)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Selected client does not exist.")

    def test_missing_model_returns_400(self):
        response = self.client.post(
            reverse("clients   existing   batch"),
            {"client": self.acme.id, "batch_code": "b0002", "version": "v1"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Device model is required.")

                                                                                                                                                                                                                              
# API layer: dropdown lookups                                                                                                                                                                                                                                
class LookupApiTests(WarehouseAPITestCase):

    def test_clients_awaiting_linking(self):
        linked = make_client("linked")
        make_batch(client=linked)
        waiting = make_client("waiting")

        response = self.client.get(reverse("clients   awaiting   linking"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [{"id": waiting.id, "client_name": "waiting"}])

    def test_client_dropdown_lists_every_client_sorted(self):
        b, a = make_client("bravo"), make_client("alpha")

        response = self.client.get(reverse("clients   list"))

        self.assertEqual(response.data, [{"id": a.id, "client_name": "alpha"}, {"id": b.id, "client_name": "bravo"}])

    def test_model_dropdown_lists_distinct_models(self):
        make_model_version(model="m", version="1")
        make_model_version(model="m", version="2")

        self.assertEqual(self.client.get(reverse("models   list")).data, [{"model": "m"}])

    def test_version_dropdown_is_scoped_to_the_model_and_normalises_the_query(self):
        v1 = make_model_version(model="pos1", version="v1")
        make_model_version(model="other", version="v9")

        response = self.client.get(reverse("versions   list"), {"model": "  POS1 "})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [{"id": v1.id, "version": "v1"}])

    def test_version_dropdown_requires_a_model(self):
        response = self.client.get(reverse("versions   list"))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "model parameter is required.")

    def test_lookups_are_closed_to_other_departments(self):
        self.authenticate_as(make_user(department=OTHER_DEPARTMENT))
        for name in ["clients   awaiting   linking", "clients   list", "models   list", "versions   list"]:
            with self.subTest(url=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, status.HTTP_403_FORBIDDEN)