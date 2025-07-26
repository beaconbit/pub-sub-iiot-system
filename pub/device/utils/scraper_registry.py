# This file uses decorators
# @decorator is shorthand for func = decorator(func)
# @register_scraper("json_http") registers a scraping function under a string key

from typing import List
from typing import Callable
import json
import requests
from utils.logging import setup_logger

logger = setup_logger(__name__)

scraper_registry: dict[str, Callable] = {}

# helper function to add functions to the scraper registry
def register_scraper(name: str):
    def wrapper(func: Callable):
        scraper_registry[name] = func
        return func
    return wrapper

@register_scraper("spindle_device")
def scrape_from_spindle_device(device: dict) -> List[int]:
    logger.info(f"Scraping device mac: {device.get('mac')}, ip: {device.get('ip')} with cookie: {device.get('cookie')}")
    ip = device["ip"]
    cookie = device["cookie"]
    device_data_readings = []

    url = f'http://{ip}/di_value/slot_0'
    logger.info(f"scraping {url}")
    headers = {'Cookie': f'adamsessionid={cookie}'}
    response = requests.get(url, headers=headers)
    json_text = response.text
    logger.info(f"{device.get('mac')} json returned during scraping: {json_text}")
    parsed_data = json.loads(json_text)
    logger.info(f"parsed data from returned json: {parsed_data}")
    di_val = parsed_data["DIVal"]
    for val in di_val:
        device_data_readings.append(val["Val"])
    return device_data_readings

