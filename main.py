"""
Main script for plugin.video.edx

Parses input, and passes values to handler
"""
import sys
import urlparse
import xbmcplugin  # pylint: disable=import-error

from resources.api_client import EdxClient
from resources.handler import handle, settings_error


# Argument parsing
PLUGIN_URL = sys.argv[0]
PLUGIN_HANDLE = int(sys.argv[1])
ARGS = urlparse.parse_qs(sys.argv[2][1:])
MODE = ARGS.get('mode', None)
CURRENT_KEY = ARGS.get('cur_key', None)


# Get plugin settings
BASE_URL = xbmcplugin.getSetting(PLUGIN_HANDLE, 'base_url')
USERNAME = xbmcplugin.getSetting(PLUGIN_HANDLE, 'username')
USER_PASSWORD = xbmcplugin.getSetting(PLUGIN_HANDLE, 'password')
OAUTH2_CLIENT_ID = 'plugin.video.edx.hackathon_dev_id'


if not BASE_URL or not USERNAME or not USER_PASSWORD:
    settings_error()
else:
    CLIENT = EdxClient(BASE_URL, OAUTH2_CLIENT_ID, USERNAME, USER_PASSWORD)
    handle(MODE, CURRENT_KEY, CLIENT, PLUGIN_HANDLE, PLUGIN_URL)
