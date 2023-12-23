import re

from ryu.base import app_manager
from ryu.controller import ofp_event
from ncclient import manager

from src.events import EventControllerReady

# Responsible for managing NETCONF communication with NETCONF devices
class NetconfController(app_manager.RyuApp):
    _EVENTS = [EventControllerReady]

    def __init__(self, *args, **kwargs):
        super(NetconfController, self).__init__(*args, **kwargs)

    def start(self):
        super(NetconfController, self).start()
        self.devices = self.connect_devices()
        

    # Read IP addresses from the config file, and returns list
    def read_config(self):
        addresses = []
        with open('config/netconf.txt', 'r') as file:
            for line in file.read().splitlines():
                if line.strip() == '' or line[0] == '#':
                    continue
                if re.match(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', line):
                    addresses.append(line)
                else:
                    self.logger.error(f'Invalid IP address: {line}')
        return addresses
    
    # Establish NETCONF connections with devices, and returns a dictionary of NETCONF managers
    def connect_devices(self):
        devices = {}
        for ip_address in self.read_config():
            try:
                device_manager = manager.connect(
                    host=ip_address,
                    port=830,
                    username='azzam',
                    password='password',
                    hostkey_verify=False
                )
                devices[ip_address] = device_manager
            except Exception as e:
                self.logger.error(f'Failed to establish NETCONF connection with {ip_address}: {str(e)}')

        self.send_event_to_observers(EventControllerReady(str(devices.keys())))
        return devices
