import os
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from utils.constants import *
from utils.exceptions import *


def get_credentials():
    """Read locally stored credentials file for API authorization."""
    if not os.path.exists(CREDS_PATH):
        return {}

    with open(CREDS_PATH) as f:
        creds = json.load(f)

    return creds


def refresh(auth_code=None):
    """Refresh Spotify access token.

    Optional arguments:
    auth_code -- if supplied, pulls new access and refresh tokens.
    """
    post_data = {}
    if auth_code:
        post_data = {'auth_code': auth_code}
    else:
        refresh_token = get_credentials().get('refresh_token')
        if refresh_token:
            post_data = {'refresh_token': refresh_token}
        else:
            raise AuthorizationError

    req = Request(
        REFRESH_URI,
        json.dumps(post_data).encode('ascii'),
        DEFAULT_HEADERS,
        method='POST'
    )
    with urlopen(req) as refresh_res:
        try:
            refresh_data = json.load(refresh_res)
            assert 'access_token' in refresh_data.keys()
        except:
            raise AuthorizationError

    creds = get_credentials()
    creds.update(refresh_data)
    if auth_code:
        creds['auth_code'] = auth_code

    with open(CREDS_PATH, 'w+') as f:
        json.dump(creds, f)

    return refresh_data


def _handle_request(endpoint, method='GET', data=None, headers={}):
    if endpoint.startswith('/'):
        endpoint = endpoint[1:]

    if data:
        data = json.dumps(data).encode('ascii')
        
    req = Request(
        API_URL + endpoint,
        data,
        headers,
        method=method
    )

    try:
        with urlopen(req) as res:
            if res.status == 200:
                return json.load(res)
            elif res.status == 204:
                return {}
    except HTTPError as e:
        if e.status == 401:
            raise TokenExpired


def request(endpoint, method='GET', data=None, headers=DEFAULT_HEADERS):
    """Request wrapper for Spotify API endpoints. Handles errors, authorization,
    and refreshing access if needed.
    """
    access_token = get_credentials().get('access_token')
    if not access_token:
        raise AuthorizationError

    headers['Authorization'] = 'Bearer ' + access_token
    try:
        data = _handle_request(endpoint, method=method, data=data, headers=headers)
    except TokenExpired:
        # refresh & retry if expired
        access_token = refresh()['access_token']
        headers['Authorization'] = 'Bearer ' + access_token
        data = _handle_request(endpoint, method=method, data=data, headers=headers)

    return data
