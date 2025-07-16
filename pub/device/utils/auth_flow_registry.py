# This file uses decorators
# @decorator is shorthand for func = decorator(func)
# @register_auth_flow("spindle_device") register an auth flow function under a string key

from typing import Callable
from bs4 import BeautifulSoup
import requests
import hashlib
from utils.logging import setup_logger

logger = setup_logger(__name__)

auth_flow_registry: dict[str, Callable] = {}

# helper function to add function to the auth flow registry
def register_auth_flow(name: str):
    def wrapper(func: Callable):
        auth_flow_registry[name] = func
        return func
    return wrapper

@register_auth_flow("spindle_device")
def auth_spindle_device(device: dict) -> str:
    username = device['username']
    password = device['password']
    # username="root"
    # password="ubuntu"
    ip = device['ip']
    #password="10011230"
    url = f"http://{ip}/config"
    hash_output = ""
    response = requests.get(url)
    response.raise_for_status() # Raises an error if the status code isn't 200
    content_type = response.headers.get("Content-Type", "")
    html_response = response.text
    logger.info(f"suth flow html response text: {html_response}")
    soup = BeautifulSoup(html_response, 'html.parser')
    logger.info(f"Beautiful Soup'd response {soup}")
    seeddata_input = soup.find('input', {'name': 'seeddata'})
    logger.info(f"seed data found: {seeddata_input}")
    if seeddata_input:
        seeddata_value = seeddata_input['value']
        hash_input =  f"{seeddata_value}:{username}:{password}"
        hash_output = hashlib.md5(hash_input.encode()).hexdigest()
    else:
        raise RuntimeError("Could not find seed data in response: {soup}")
    cookie_name = ""
    cookie_value = ""
    login_url = url + "/index.html"
    if len(hash_output) > 1:
        data = {
            "seeddata": seeddata_value,
            "authdata": hash_output
        }
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        response = requests.post(login_url, data=data, headers=headers)
        response.raise_for_status() # Raises an error if the status code isn't 200
        content_type = response.headers.get("Content-Type", "")
        html_response = response.text
        cookies = response.cookies
        for cookie in cookies:
            cookie_name = cookie.name
            cookie_value = cookie.value
    else:
        raise RuntimeError("Did not find valid hash")
    if not isinstance(cookie_value, str):
        raise TypeError("Expected cookie to be a string")
    if not cookie_value:
        raise ValueError("Cookie must not be empty")
    return cookie_value

