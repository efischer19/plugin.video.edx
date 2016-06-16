import requests
import xbmc
import xbmcaddon
import xbmcgui

from collections import defaultdict

# Security hole: do not release until this is removed, which will not be possible until the python version
# bundled with Kodi gets upgraded in the upcoming Krypton release. https://github.com/xbmc/xbmc/pull/8207
requests.packages.urllib3.disable_warnings()
# Addt'l note for python version bump: we can remove the string concats for format() at that time too

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

    def get_response_data(self, url):
        """
        GETs a url, using a previously acquired access_token
        """
        assert self.has_access_token()
        headers = {'Authorization': 'Bearer ' + self.__access_token}
        response = requests.get(url, headers=headers)
        assert response.status_code == 200
        return response.json()

    def get_courses(self):
        url = BASE_URL + 'api/courses/v1/courses/?username=audit&page_size=2000'
        xbmc.log('edx get_mobile_courses url: ' + url)
        data = self.get_response_data(url)
        return data['results']


class Course(object):
    """
    Contains all the relevant info for the user's courses
    """

    def __init__(self, name, number, org, media, api_url):
        """
        Assign the parameters to instance vars

        params:
            name: string - used as directory title
            number: string
            org: string
            media: dict containing keys [course_image, course_video, image [raw, small, large]]
            api_url: the api to be used for further api requests for this course
        """
        self.name = name
        self.number = number
        self.org = org
        self.media = media
        self.api_url = api_url

    def __repr__(self):
        return "{0} {1}: {2}".format(self.org, self.number, self.name)

    @classmethod
    def build_from_results(cls, results):
        """
        Builds and returns a list of Course objects, given a course listing result.
        """
        return [
            Course(r['name'], r['number'], r['org'], r['media'], r['blocks_url'])
            for r in results
        ]


ADDON_NAME = xbmcaddon.Addon().getAddonInfo('name')

if __name__ == "__main__":
    client = EdxClient()
    client.get_access_token()
    courses = Course.build_from_results(client.get_courses())
    xbmc.log('edX course listing: ' + str(courses))
    xbmcgui.Dialog().ok(ADDON_NAME, 'SUCCESS')


#https://efischer19.sandbox.edx.org/api/courses/v1/blocks/?course_id=course-v1%3AedX%2BDemoX%2BDemo_Course&username=staff&depth=all&block_types_filter=video&student_view_data=video
