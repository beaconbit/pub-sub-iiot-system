from device.utils.auth_flow_registry import auth_flow_registry
from device.utils.scraper_registry import scraper_registry
from utils.logging import setup_logger
from config import load_config

logger = setup_logger(__name__)

def brute_force(device: dict) -> bool:
    config = load_config()
    password = None
    username = None
    auth_flow = None
    scraper = None
    cookie = None
    for cred in config.get("credentials", []):
        try: 
            device['password'] = cred['password']
            device['username'] = cred['username']
            password, username, auth_flow, scraper, cookie = check_credentials(device, cred['password'], cred['username'])
            if password is not None and username is not None and auth_flow is not None and scraper is not None:
                break
        except Exception as e:
            continue
    return [password, username, auth_flow, scraper, cookie]

def check_credentials(device, password, username):
    logger.info(f"Brute forcing device {device.get('mac')}")
    auth_flow = None
    scraper = None
    # check if auth flow throws error
    auth_flow, cookie = test_against_auth_flows(device, password, username)
    if auth_flow is not None:
        # if auth flow works, check if scraper works
        scraper = test_against_scrapers(device, password, username, cookie)

    logger.info(f"Brute force credential discovery found {password}, {username}, {auth_flow}, {scraper}")
    return [password, username, auth_flow, scraper, cookie]


def test_against_auth_flows(device, password, username):
    auth_flow = None
    successfully_retrieved_cookie = None
    for key, auth_flow_fn in auth_flow_registry.items():
        try:
            successfully_retrieved_cookie = auth_flow_fn(device)
            logger.info(f"Brute force successfully retrieved cookie {successfully_retrieved_cookie} using {password} {username} {key}")
            auth_flow = key
            if successfully_retrieved_cookie is not None:
                break
        except Exception as e:
            continue
    return [auth_flow, successfully_retrieved_cookie]

def test_against_scrapers(device, password, username, cookie):
    scraper = None
    successfully_retrieved_data = None
    for key, scraper_fn in scraper_registry.items():
        try:
            device['cookie'] = cookie
            successfully_retrieved_data = scraper_fn(device)
            logger.info(f"Brute force successfully scraped {successfully_retrieved_data} using {password} {username} {key}")
            scraper = key
            if successfully_retrieved_data is not None:
                break
        except Exception as e:
            continue
    return scraper


