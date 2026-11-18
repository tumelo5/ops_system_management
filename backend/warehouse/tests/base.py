from rest_framework.test import APITestCase

from .factories import (
    WAREHOUSE_DEPARTMENT,
    make_batch,
    make_client,
    make_company,
    make_device,
    make_user,
)


class WarehouseAPITestCase(APITestCase):
    """
    API tests start as a logged-in Warehouse agent.

    ASSUMPTION: IsWarehouseAgent decides from request.user.department, so force_authenticate
    is enough. If it reads the department from the JWT claim instead, change authenticate_as()
    below to attach a real token. It is the only place that needs to change.
    """

    def setUp(self):
        super().setUp()
        self.user = make_user(department=WAREHOUSE_DEPARTMENT)
        self.authenticate_as(self.user)

    def authenticate_as(self, user):
        """Pass None to make the next requests anonymous."""
        self.client.force_authenticate(user=user)


class RentalWorldMixin:
    """
    The standard rental scenario. Call self.build_rental_world() from setUp.

      self.company       the servicing company (a Client), already set as the company
      self.customer      an ordinary client
      self.device        company-owned (its batch belongs to the company) -> rentable
      self.owned_device  client-owned (its batch belongs to the customer) -> NOT rentable
    """

    def build_rental_world(self):
        self.company = make_client("johndoe")
        make_company(self.company)
        self.customer = make_client("customer")
        self.device = make_device(batch=make_batch(batch_code="cmp01", client=self.company))
        self.owned_device = make_device(batch=make_batch(batch_code="cus01", client=self.customer))