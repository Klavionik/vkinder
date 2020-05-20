import logging
import os
import sys
import pickle
import re
from collections import namedtuple
from getpass import getpass
from time import sleep

import mechanize
import requests
# noinspection PyPackageRequirements
from oauthlib.oauth2 import MobileApplicationClient
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import MismatchingStateError

from vkinder.exceptions import APIError, \
    InternalServerError, TooManyRequestsPerSecond, UserUnavailable, InvalidUserID
from . import config, root, tokenpath, Y, END, G, R
from .utils import clean_screen

CLIENT_ID = config.get('App Settings', 'ClientID',
                       fallback=os.environ.get('CLIENT_ID'))
AUTHORIZE_URL = config.get('VK API', 'AuthorizeUrl')
REDIRECT_URI = config.get('VK API', 'RedirectUrl')

UsersMethods = namedtuple('Users', 'get search')
GroupsMethods = namedtuple('Groups', 'get')
OtherMethods = namedtuple('Others', 'getcities execute')

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s')


def open_token():
    with open(tokenpath, "rb") as f:
        token = pickle.load(f)

    return token


def save_token(token):
    with open(tokenpath, "wb") as f:
        pickle.dump(token, f)


def check_profile(usergetmethod):
    def wrapper(*args, **kwargs):
        response = usergetmethod(*args, **kwargs)

        if response[0].get('is_closed') or response[0].get('deactivated'):
            raise UserUnavailable("User is not available")

        return response

    return wrapper


class VKApi:

    def __init__(self, api_url, api_version, debug):
        self.url = api_url
        self.v = api_version
        self.token = self.authorize()
        self.auth = {'v': self.v, 'access_token': self.token}
        self.users = UsersMethods(get=self._users_get, search=self._users_search)
        self.groups = GroupsMethods(get=self._groups_get)
        self.other = OtherMethods(getcities=self._get_cities, execute=self._execute)

        if debug:
            fileh = logging.FileHandler(os.path.join(root, 'api.log'))
            fileh.setFormatter(formatter)
            logger.addHandler(fileh)

        self._test_request()

    def authorize(self, discard_token=False):
        """
        Handles authorization process at the start of the application.
        Tries to read token from a file and if it fails, runs get_token()
        to obtain a new token from a user.

        :param discard_token: If True save token to a file
        :return: VK API token
        """

        try:
            token = open_token()
        except FileNotFoundError:
            try:
                token = self._get_token(discard_token)
            except MismatchingStateError:
                print(f'{R}Mismatching state: possible CSFR attack '
                      f'or you just typed in a wrong authentication code{END}')
                sys.exit()

        return token

    def _users_get(self, **kwargs):
        return self._get_response('/users.get',
                                  request_params=kwargs)

    def _users_search(self, **kwargs):
        return self._get_response('/users.search',
                                  request_params=kwargs)

    def _execute(self, **kwargs):
        return self._get_response('/execute',
                                  request_params=kwargs)

    def _groups_get(self, **kwargs):
        return self._get_response('/groups.get',
                                  request_params=kwargs)

    def _get_cities(self, **kwargs):
        return self._get_response('/database.getCities',
                                  request_params=kwargs)

    def _get_response(self, method, request_params):

        params = {**self.auth, **request_params}

        response = None
        success = False
        retry = 5

        while not success:
            try:
                logger.debug(f'Request started: method {method}\nParameters {request_params}')
                response = self._send_request(self.url + method, params)
            except TooManyRequestsPerSecond:
                logger.debug('Handling TooManyRequestsPerSecond exception')
                sleep(0.3)
                continue
            except InternalServerError:
                logger.debug('Handling InternalServerError exception, '
                             f'attempts left {retry}')
                if retry > 0:
                    retry -= 1
                    continue
                else:
                    raise
            else:
                logger.debug(f'Response acquired\n')
                success = True

        return response

    @staticmethod
    def _send_request(url, params):

        response = requests.request('POST', url, data=params, timeout=20)

        if response.status_code == 200:
            json_response = response.json()

            if error := json_response.get('error'):
                if error['error_code'] == 6:
                    raise TooManyRequestsPerSecond('VK API allows only 3 requests/sec',
                                                   error=error)
                elif error['error_code'] == 10:
                    raise InternalServerError('VK API internal server error',
                                              error=error)
                elif error['error_code'] == 113:
                    raise InvalidUserID("User doesn't exist", error=error)
                else:
                    logger.debug(f'VK API Error: {error}')
                    raise APIError('VK API error', error=error)

            return json_response['response']
        else:
            response.raise_for_status()

    def _get_token(self, discard_token):
        """
        Establishes an OAuth2 session to retrieve a token for further API requests.
        Saves retrieved token to a file.

        :param discard_token: If True save token to a file
        :return: VK API token
        """
        print(f'{Y}VKInder\nWe need to authorize you with VK{END}\n')

        with OAuth2Session(client=MobileApplicationClient(client_id=CLIENT_ID),
                           redirect_uri=REDIRECT_URI,
                           scope="friends, groups, offline, photos") as vk:
            authorization_url, state = vk.authorization_url(AUTHORIZE_URL)
            tokenurl = self._login(authorization_url)
            vk.token_from_fragment(tokenurl)
            token = vk.access_token

            if not discard_token:
                save_token(token)
                with open('token.txt', 'w') as f:
                	f.write(token)

        return token

    @staticmethod
    def _login(authorization_url, login_attempts=3):
        browser = mechanize.Browser()
        browser.set_handle_robots(False)
        allowlink = re.compile(r'(https://login\.vk\.com/\?act=grant_access.*?html)')

        browser.open(authorization_url)
        while login_attempts:
            if AUTHORIZE_URL in browser.geturl():
                browser.select_form(nr=0)
                print(f'Login attempts left: {login_attempts}')
                browser.form['email'] = input('Enter your VK email or phone number:\n')
                browser.form['pass'] = getpass('Enter your VK password:\n')
                browser.submit()
            else:
                break
            login_attempts -= 1
        else:
            print("Invalid login and/or password!")
            sys.exit()
        if 'authcheck' in browser.geturl():
            browser.select_form(nr=0)
            browser.form['code'] = input('Enter authentication code\n')
            browser.submit()
        try:
            raw_response = browser.response()
            decoded_response = raw_response.get_data().decode('cp1251')
            match = re.search(allowlink, decoded_response)
            link = match.group(0)
            permission = input("You are about to grant next permissions to this app:\n"
                               "Access to friends\n"
                               "Access to photos\n"
                               "Access to API at any time\n\n"
                               "Proceed? y/n").lower().rstrip()
            if permission != 'y':
                print('Aborted')
                sys.exit()
            browser.open(link)
        except AttributeError:
            pass

        tokenurl = browser.geturl()
        return tokenurl

    def _test_request(self):
        response = self.users.get()
        owner_name = response[0]['first_name']
        owner_surname = response[0]['last_name']
        clean_screen()

        print(f"{G}Authorized as: {owner_name} {owner_surname}{END}")
