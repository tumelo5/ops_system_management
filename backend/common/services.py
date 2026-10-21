

# Functions used system-wide for device-related operations, such as retrieving devices by serial number.
class DeviceService:

    @staticmethod
    def get_device_by_serial_number(serial_number):
        try:
            return Device.objects.get(serial_number=serial_number)
        except Device.DoesNotExist:
            raise ValueError(f"Device with serial number '{serial_number}' does not exist.")