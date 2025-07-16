import threading
import time
from utils.logging import setup_logger
from scapy.all import ARP, Ether, srp
from bs4 import BeautifulSoup
import requests
import socket
import netifaces
from master.device_registry import get_registry


logger = setup_logger(__name__)

class ScannerThread(threading.Thread):
    def __init__(self, config):
        super().__init__()
        self.daemon = True
        self.running = True
        self.scan_interval = config.get("scan_interval", 30)
        self.ip_interface = config.get("process", {}).get("interface", "eth0") 
        self.public_ip = config.get("process", {}).get("public_ip", None)

    def run(self):
        logger.info("Scanner loop starting")
        while self.running:
            self.scan_network()
            time.sleep(self.scan_interval)

    # def get_ip(interface):
    #         addrs = netifaces.ifaddresses(interface)
    #         return addrs[netifaces.AF_INET][0]['addr']
    def get_ip(self, interface):
        if self.public_ip is not None:
            return self.public_ip
        try:
            addrs = netifaces.ifaddresses(interface)
            inet_addrs = addrs.get(netifaces.AF_INET)
            if inet_addrs:
                return inet_addrs[0].get('addr')
        except Exception as e:
            pass  # Silently ignore and fall through
        return None

    def get_local_ip(self):
        local_ip = self.get_ip(self.ip_interface)
        if local_ip is None:
            raise RuntimeError("public ip could not be found")
        return local_ip

    def add_devices_to_global_state(self, devices):
        # ***********ACCESS SHARED DEVICE REGISTRY************
        # iterate over found devices and add anything not already in registry
        for mac, ip in devices.items():
            registry = get_registry()
            device = registry.get_device(mac)
            if device is None:
                registry.add_or_update_device(mac, ip)

    def scan_network(self):
        try:
            my_ip = self.get_local_ip()
            ip_range = my_ip + "/24"
            arp = ARP(pdst=ip_range)
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether / arp
            result = srp(packet, iface="eno1", timeout=3, verbose=False)[0]
            # Extract IP and MAC addresses from the response
            devices = {} # { '<mac address>' : '<ip address>', ... }
            for sent, received in result:
                logger.debug(f'Host: {received.psrc} MAC: {received.hwsrc}')
                devices[received.hwsrc] = received.psrc
            self.add_devices_to_global_state(devices)
        except Exception as e:
            logger.error(f"Network scan failed: {e}")

    def stop(self):
        self.running = False

