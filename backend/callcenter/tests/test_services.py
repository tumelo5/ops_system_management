from django.test import TestCase

from backend.callcenter.models import DeviceLog
from backend.callcenter.services import DeviceLogService



# def test_some_behavior(self):
#     # Arrange
#     # Create the data needed

#     # Act
#     # Call the function you're testing

#     # Assert
#     # Verify the result is correct



class TestDeviceLogService(TestCase):

    # Test the create_device_log method
    def test_create_device_log(self):
        # Arrange
        serial_number = "SN123456"
        status_logged = "RECEIVED"

        # Act
        device_log = DeviceLogService.create_device_log(
            serial_number=serial_number,
            status_logged=status_logged
        )

        # Assert
        self.assertIsInstance(device_log, DeviceLog)
        self.assertIsNotNone(device_log.pk)
        self.assertEqual(device_log.serial_number, serial_number)
        self.assertEqual(device_log.status_logged, status_logged)
        self.assertEqual(DeviceLog.objects.count(), 1)

        self.assertTrue(
            DeviceLog.objects.filter(
                serial_number=serial_number,
                status_logged=status_logged
            ).exists()
        )
    
    # Test the get_latest_status method
    def test_get_latest_status_returns_most_recent_status(self):
        DeviceLog.objects.create(
            serial_number="SN001",
            status_logged="RECEIVED"
        )

        DeviceLog.objects.create(
            serial_number="SN001",
            status_logged="CONFIGURED"
        )

        status = DeviceLogService.get_latest_status("SN001")

        self.assertEqual(status, "CONFIGURED")

    def test_get_latest_status_returns_none_when_serial_number_does_not_exist(self):
        status = DeviceLogService.get_latest_status("UNKNOWN")

        self.assertIsNone(status)
 