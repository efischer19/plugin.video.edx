"""
This module contains all the logic needed to talk to edX APIs
"""
import requests


# Because of the python version used by Kodi, this is needed to avoid SSL
# warnings. Can be removed on upgrade to Karma.
requests.packages.urllib3.disable_warnings()


class EdxClient(object):
    """
    A class containing all the "talk to edx servers" functionality needed by this plugin.
    """

    def __init__(self, base_url, oauth_id, username, password):
        self.base_url = base_url
        self.access_token_url = self.base_url + 'oauth2/access_token/'
        self.__oauth_id = oauth_id
        self.__username = username
        self.__password = password
        self.__access_token = ''

    def get_access_token(self):
        """
        Uses class constants (eventually settings values) to get an access token
        """
        response = requests.post(
            self.access_token_url,
            data={
                'client_id': self.__oauth_id,
                'grant_type': 'password',
                'username': self.__username,
                'password': self.__password
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
        """
        Gets all the courses the user is currently enrolled in.
        """
        url = "{0}{1}{2}{3}{4}".format(
            self.base_url,
            "api/courses/v1/courses/",
            "?username=",
            self.__username,
            "&page_size=2000"
        )
        data = self.get_response_data(url)
        return data['results']

    def get_course_blocks(self, base_course_url):
        """
        url is constructed to get all video blocks, as well as all structure blocks
        """
        url = "{0}{1}{2}{3}{4}{5}{6}".format(
            base_course_url,
            "&username=",
            self.__username,
            "&depth=all",
            "&block_types_filter=video,course,chapter,sequential,vertical",
            "&requested_fields=children",
            "&student_view_data=video"
        )
        data = self.get_response_data(url)
        return data['blocks'], data['root']
