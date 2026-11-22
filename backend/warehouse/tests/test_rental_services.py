"""
Rental business rules, at the service layer: CompanyService and DeviceRentalService.

Scenario (see RentalWorldMixin in base.py):
  self.company       the servicing company, already set
  self.customer      an ordinary client
  self.device        company owned   > rentable
  self.owned_device  client owned    > never rentable
"""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from ..models import CompanyProfile, DeviceRental
from ..services import (
    CompanyAlreadySet,
    CompanyService,
    DeviceNotFound,
    DeviceRentalService,
    RentalConflict,
)
from .base import RentalWorldMixin
from .factories import make_batch, make_client, make_company, make_device, make_rental, make_user

Service = DeviceRentalService

def end_one(rental_id, end_date):
    """Ending one rental is the bulk method with a single id."""
    return Service.end_rentals([rental_id], end_date)[0]

def item(device, client, expected_return_date=None):
    return {"device": device, "rental_client": client, "expected_return_date": expected_return_date}

                                                                          
# Company (set once)                                                                         
class CompanyServiceTests(TestCase):

    def test_company_is_none_until_it_is_set(self):
        self.assertIsNone(CompanyService.get_company_client_or_none())

    def test_getting_an_unset_company_raises_a_rental_conflict(self):
        with self.assertRaisesMessage(RentalConflict, "has not been set up yet"):
            CompanyService.get_company_client()

    def test_set_company_stores_the_client_and_who_set_it(self):
        acme, user = make_client("acme"), make_user()

        profile = CompanyService.set_company(client=acme, user=user)

        self.assertEqual((profile.client, profile.set_by), (acme, user))
        self.assertEqual(CompanyService.get_company_client(), acme)

    def test_company_can_only_be_set_once_even_to_a_different_client(self):
        CompanyService.set_company(client=make_client("first"), user=None)

        for other in [make_client("second"), CompanyProfile.objects.get().client]:
            with self.subTest(client=other.client_name):
                with self.assertRaises(CompanyAlreadySet):
                    CompanyService.set_company(client=other, user=None)

        self.assertEqual(CompanyProfile.objects.count(), 1)
        self.assertEqual(CompanyService.get_company_client().client_name, "first")

    def test_company_cannot_be_unset(self):
        profile = make_company()

        with self.assertRaises(RuntimeError):
            profile.delete()

                                                                           
# Ownership and scan time check                                                                        
class OwnershipAndCheckTests(RentalWorldMixin, TestCase):

    def setUp(self):
        self.build_rental_world()

    def test_device_is_company_owned_when_its_batch_belongs_to_the_company(self):
        self.assertTrue(Service.is_company_owned(self.device))
        self.assertFalse(Service.is_company_owned(self.owned_device))

    def test_ownership_check_needs_the_company_to_be_set(self):
        CompanyProfile.objects.all().delete()  # queryset delete bypasses the model's guard

        with self.assertRaises(RentalConflict):
            Service.is_company_owned(self.device)

    def test_check_rentable_returns_the_device(self):
        self.assertEqual(Service.check_rentable(f"  {self.device.serial_number}  "), self.device)

    def test_check_rentable_unknown_device(self):
        with self.assertRaises(DeviceNotFound):
            Service.check_rentable("does not exist")

    def test_check_rentable_rejects_client_owned_device(self):
        with self.assertRaisesMessage(RentalConflict, "not company-owned"):
            Service.check_rentable(self.owned_device.serial_number)

    def test_check_rentable_rejects_device_that_is_not_active(self):
        for end_state in ["SCRAPPED", "DECOMMISSIONED"]:
            with self.subTest(status=end_state):
                self.device.device_status = end_state
                self.device.save()
                with self.assertRaisesMessage(RentalConflict, "not available for rental"):
                    Service.check_rentable(self.device.serial_number)

    def test_check_rentable_rejects_device_already_on_rent(self):
        make_rental(self.device, self.customer)

        with self.assertRaisesMessage(RentalConflict, "already rented out"):
            Service.check_rentable(self.device.serial_number)

    def test_check_rentable_accepts_device_whose_rental_has_ended(self):
        make_rental(self.device, self.customer, returned_at=timezone.localdate())

        self.assertEqual(Service.check_rentable(self.device.serial_number), self.device)

    def test_check_rentable_needs_the_company_to_be_set(self):
        CompanyProfile.objects.all().delete()

        with self.assertRaisesMessage(RentalConflict, "has not been set up yet"):
            Service.check_rentable(self.device.serial_number)

                                                                          
# Assigning rentals                                                                        
class CreateRentalsTests(RentalWorldMixin, TestCase):

    def setUp(self):
        self.build_rental_world()
        self.second_device = make_device(batch=self.device.batch)  # also company owned

    def test_creates_active_rentals(self):
        due = timezone.now() + timedelta(days=30)

        rentals = Service.create_rentals([
            item(self.device, self.customer, due),
            item(self.second_device, self.customer),
        ])

        self.assertEqual(len(rentals), 2)
        first = rentals[0]
        self.assertEqual((first.device, first.rental_client, first.expected_return_date), (self.device, self.customer, due))
        self.assertIsNone(first.returned_at)
        self.assertTrue(first.is_active)
        self.assertIsNone(rentals[1].expected_return_date)

    def test_renting_never_changes_the_device_or_its_batch(self):
        batch, owner = self.device.batch, self.device.batch.client

        Service.create_rentals([item(self.device, self.customer)])

        self.device.refresh_from_db()
        batch.refresh_from_db()
        self.assertEqual(self.device.batch, batch)
        self.assertEqual(batch.client, owner)
        self.assertEqual(self.device.device_status, "ACTIVE")

    def test_client_owned_device_cannot_be_rented(self):
        other = make_client("other")

        with self.assertRaisesMessage(RentalConflict, "not company-owned"):
            Service.create_rentals([item(self.owned_device, other)])

        self.assertEqual(DeviceRental.objects.count(), 0)

    def test_device_cannot_be_rented_to_the_company_itself(self):
        with self.assertRaisesMessage(RentalConflict, "cannot be rented to the company that owns it"):
            Service.create_rentals([item(self.device, self.company)])

    def test_device_that_is_already_on_rent_cannot_be_rented_again(self):
        make_rental(self.device, self.customer)

        with self.assertRaisesMessage(RentalConflict, "already rented out"):
            Service.create_rentals([item(self.device, make_client("other"))])

        self.assertEqual(DeviceRental.objects.count(), 1)

    def test_same_device_twice_in_one_request_is_rejected(self):
        with self.assertRaisesMessage(RentalConflict, "appears more than once"):
            Service.create_rentals([item(self.device, self.customer), item(self.device, self.customer)])

        self.assertEqual(DeviceRental.objects.count(), 0)

    def test_one_bad_device_means_no_rentals_at_all(self):
        with self.assertRaises(RentalConflict):
            Service.create_rentals([
                item(self.device, self.customer),        # fine
                item(self.owned_device, self.customer),  # client owned  > blocks the batch
            ])

        self.assertEqual(DeviceRental.objects.count(), 0)

    def test_renting_needs_the_company_to_be_set(self):
        CompanyProfile.objects.all().delete()

        with self.assertRaisesMessage(RentalConflict, "has not been set up yet"):
            Service.create_rentals([item(self.device, self.customer)])

    def test_device_can_be_rented_again_after_the_rental_ends_and_history_is_kept(self):
        first = Service.create_rentals([item(self.device, self.customer)])[0]
        end_one(first.pk, timezone.localdate())

        second = Service.create_rentals([item(self.device, make_client("later"))])[0]

        self.assertEqual(self.device.rentals.count(), 2)
        self.assertNotEqual(first.pk, second.pk)

    def test_database_allows_only_one_active_rental_per_device(self):
        # The service checks first; this proves the DB constraint is the backstop for races.
        make_rental(self.device, self.customer)

        with self.assertRaises(IntegrityError), transaction.atomic():
            make_rental(self.device, make_client("other"))

    def test_database_allows_a_new_active_rental_beside_ended_ones(self):
        make_rental(self.device, self.customer, returned_at=timezone.localdate())
        make_rental(self.device, self.customer, returned_at=timezone.localdate())

        make_rental(self.device, self.customer)  # does not raise

                                                                          
# Looking up and ending rentals                                                                           
class EndRentalTests(RentalWorldMixin, TestCase):

    def setUp(self):
        self.build_rental_world()
        self.rental = make_rental(self.device, self.customer)

    def backdate_start(self, days):
        DeviceRental.objects.filter(pk=self.rental.pk).update(start_date=timezone.now() - timedelta(days=days))

    #     active lookup    

    def test_active_rental_is_found_by_serial_number_ignoring_surrounding_spaces(self):
        found = Service.get_active_rental(f" {self.device.serial_number} ")

        self.assertEqual(found, self.rental)

    def test_no_active_rental_once_it_has_ended(self):
        end_one(self.rental.pk, timezone.localdate())

        self.assertIsNone(Service.get_active_rental(self.device.serial_number))

    #end one    

    def test_ending_a_rental_records_the_end_date(self):
        today = timezone.localdate()

        ended = end_one(self.rental.pk, today)

        self.assertEqual(ended.returned_at, today)
        self.rental.refresh_from_db()
        self.assertEqual(self.rental.returned_at, today)
        self.assertFalse(self.rental.is_active)

    def test_end_date_can_be_any_day_from_the_start_date_to_today(self):
        self.backdate_start(5)

        end_one(self.rental.pk, timezone.localdate() - timedelta(days=3))

        self.rental.refresh_from_db()
        self.assertEqual(self.rental.returned_at, timezone.localdate() - timedelta(days=3))

    def test_end_date_before_the_start_date_is_rejected(self):
        self.backdate_start(5)

        with self.assertRaisesMessage(RentalConflict, "before the rental start date"):
            end_one(self.rental.pk, timezone.localdate() - timedelta(days=10))

    def test_end_date_in_the_future_is_rejected(self):
        with self.assertRaisesMessage(RentalConflict, "cannot be in the future"):
            end_one(self.rental.pk, timezone.localdate() + timedelta(days=1))

    def test_ending_an_ended_rental_is_rejected(self):
        end_one(self.rental.pk, timezone.localdate())

        with self.assertRaisesMessage(RentalConflict, "already been ended"):
            end_one(self.rental.pk, timezone.localdate())

    def test_ending_an_unknown_rental_is_rejected(self):
        with self.assertRaisesMessage(RentalConflict, "Rental 999999 does not exist."):
            end_one(999999, timezone.localdate())

    def test_device_is_rentable_again_after_its_rental_ends(self):
        end_one(self.rental.pk, timezone.localdate())

        Service.check_rentable(self.device.serial_number)  # does not raise

    #end many    

    def test_ends_many_rentals_with_one_shared_date_in_order(self):
        other_device = make_device(batch=self.device.batch)
        other = make_rental(other_device, self.customer)
        today = timezone.localdate()

        ended = Service.end_rentals([other.pk, self.rental.pk], today)

        self.assertEqual([r.pk for r in ended], [other.pk, self.rental.pk])
        self.assertEqual(DeviceRental.objects.filter(returned_at=today).count(), 2)

    def test_bulk_end_is_all_or_nothing(self):
        other = make_rental(make_device(batch=self.device.batch), self.customer, returned_at=timezone.localdate())

        with self.assertRaises(RentalConflict) as caught:
            Service.end_rentals([self.rental.pk, other.pk], timezone.localdate())  # second is already ended

        self.assertIn(other.device.serial_number, str(caught.exception))  # names the blocking device
        self.rental.refresh_from_db()
        self.assertIsNone(self.rental.returned_at)  # the good one was NOT ended

    def test_bulk_end_rejects_unknown_and_repeated_ids(self):
        with self.assertRaisesMessage(RentalConflict, "Rental 999999 does not exist."):
            Service.end_rentals([self.rental.pk, 999999], timezone.localdate())
        with self.assertRaisesMessage(RentalConflict, "appears more than once"):
            Service.end_rentals([self.rental.pk, self.rental.pk], timezone.localdate())

        self.rental.refresh_from_db()
        self.assertIsNone(self.rental.returned_at)

                                                                           
# Operational client (the contract Repairs / Production will use)                                                                           
class ResolveOperationalClientTests(RentalWorldMixin, TestCase):

    def setUp(self):
        self.build_rental_world()

    def test_unknown_serial_number_is_rejected(self):
        with self.assertRaises(DeviceNotFound):
            Service.resolve_operational_client("does not exist")

    def test_without_a_rental_the_batch_client_is_the_operational_client(self):
        client, source = Service.resolve_operational_client(self.owned_device.serial_number)

        self.assertEqual((client, source), (self.customer, "BATCH"))

    def test_an_active_rental_takes_priority_over_the_batch_client(self):
        make_rental(self.device, self.customer)

        client, source = Service.resolve_operational_client(self.device.serial_number)

        self.assertEqual((client, source), (self.customer, "RENTAL"))

    def test_after_the_rental_ends_it_falls_back_to_the_batch_client(self):
        rental = make_rental(self.device, self.customer)
        end_one(rental.pk, timezone.localdate())

        client, source = Service.resolve_operational_client(self.device.serial_number)

        self.assertEqual((client, source), (self.company, "BATCH"))

    def test_the_permanent_owner_is_never_changed_by_renting(self):
        make_rental(self.device, self.customer)

        self.device.refresh_from_db()
        self.assertEqual(self.device.batch.client, self.company)