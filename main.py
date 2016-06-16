import requests
import xbmcaddon
import xbmcgui

from collections import defaultdict

USERNAME='audit'
USER_PASSWORD='edx'
OAUTH2_CLIENT_ID='plugin.video.edx.hackathon_dev_id'
OAUTH2_URL='https://efischer19.sandbox.edx.org/oauth2/access_token/'
ACCESS_TOKEN=''

addon_name = xbmcaddon.Addon().getAddonInfo('name')

def get_access_token():
    response = requests.post(
        OAUTH2_URL,
        data={
            'client_id': OAUTH2_CLIENT_ID,
            'grant_type': 'password',
            'username': USERNAME,
            'password': USER_PASSWORD
        },
    )
    return response.json()['access_token']

if __name__ == "__main__":
    ACCESS_TOKEN = get_access_token()
    xbmcgui.Dialog().ok(addon_name, ACCESS_TOKEN)
