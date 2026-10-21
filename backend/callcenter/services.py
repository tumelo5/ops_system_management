from .models import DeviceLog




class DeviceLogService:
    @staticmethod
    def create_device_log(serial_number: str, status_logged: str) -> DeviceLog:
        """
        Create a new DeviceLog entry.
        :param serial_number: The serial number of the device.
        :param status_logged: The status logged for the device.
        """
        device_log = DeviceLog.objects.create(serial_number=serial_number, status_logged=status_logged)
        return device_log


    @staticmethod
    def get_latest_status(serial_number: str) -> Optional[str]:
        """
        Retrieve a device's latest status by its serial number.

        :param serial_number: The serial number of the device.
        :return: Latest status if found, otherwise None.
        """
        return (
            DeviceLog.objects
            .filter(serial_number=serial_number)
            .order_by("-date_logged")
            .values_list("status_logged", flat=True)
            .first()
        )

  

