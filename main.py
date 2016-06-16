import requests
import xbmcaddon
import xbmcgui

from collections import defaultdict

# I'm using global constants for all these rn, instead of figuring out addon settings properly
# that'll come later
BASE_URL = 'https://efischer19.sandbox.edx.org/'
USERNAME = 'audit'
USER_PASSWORD = 'edx'
OAUTH2_CLIENT_ID = 'plugin.video.edx.hackathon_dev_id'

class EdxClient(object):
    """
    A class containing all the "talk to edx servers" functionality needed by this plugin.
    """
    access_token_url = BASE_URL + 'oauth2/access_token/'

    def __init__(self):
        __access_token = ''

    def get_access_token(self):
        """
        Uses class constants (eventually settings values) to get an access token
        """
        response = requests.post(
            EdxClient.access_token_url,
            data={
                'client_id': OAUTH2_CLIENT_ID,
                'grant_type': 'password',
                'username': USERNAME,
                'password': USER_PASSWORD
            },
        )
        self.__access_token = response.json()['access_token']

    def has_access_token(self):
        return self.__access_token != ''


ADDON_NAME = xbmcaddon.Addon().getAddonInfo('name')

if __name__ == "__main__":
    client = EdxClient()
    client.get_access_token()
    xbmcgui.Dialog().ok(ADDON_NAME, str(client.has_access_token()))
