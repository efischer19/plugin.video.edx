import requests
import sys
import urllib
import urlparse
import xbmc
import xbmcgui
import xbmcplugin

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
        xbmc.log('edx get_courses url: ' + url)
        data = self.get_response_data(url)
        return data['results']

    def get_course_blocks(self, base_course_url):
        # url is constructed to get all video blocks, as well as all structure blocks
        url = base_course_url + "&username=" + USERNAME + "&depth=all&block_types_filter=video,course,chapter,sequential,vertical&requested_fields=children&student_view_data=video"
        xbmc.log('edx get_course_blocks url: ' + url)
        data = self.get_response_data(url)
        return data['blocks'], data['root']


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

    def build_tree(self, blocks, root_id):
        """
        Builds and returns a dict, representing the tree for this course
        """
        class Node(object):
            def __init__(self, key):
                self.children = set()
                self.name = ''
                self.url = ''
                self.id = key
                self.should_prune = True

            def __hash__(self):
                return hash(self.id)

            def is_leaf(self):
                return len(self.children) == 0

            def pruning_walk(self, node_set):
                if self.is_leaf() and self.url:
                    self.should_prune = False
                    return False
                for child in [
                        node
                        for node in node_set
                        if node.id in [
                            child.id
                            for child in self.children
                        ]
                    ]:
                    if not child.pruning_walk(node_set):
                        self.should_prune = False
                return self.should_prune

            def to_dict(self, node_set):
                if self.is_leaf():
                    return {
                        'id': self.id,
                        'name': self.name,
                        'url': self.url
                    }
                return {
                    'id': self.id,
                    'name': self.name,
                    'children': [
                        node.to_dict(node_set)
                        for node in node_set
                        if node.id in [
                            child.id
                            for child in self.children
                        ]
                    ]
                }

        # setup Node tracking
        node_set = set()

        # Build Node objects
        for key, value in blocks.iteritems():
            node = Node(key)
            node.name = value['display_name']
            try:
                if value['type'] != 'video':
                    node.children = [Node(child) for child in value['children']]
                else:
                    urls = [val['url'] for key, val in value['student_view_data']['encoded_videos'].iteritems()]
                    node.url = urls[0]  # should only be one per here
            except KeyError:
                pass  # if something went wrong, we won't be able to play this video node, or the non-video node has no children
            node_set.add(node)

        # Prune invalid paths (branches with no video)
        root = next(node for node in node_set if node.id == root_id)
        root.pruning_walk(node_set)
        for node in [node for node in node_set if node.should_prune]:
            xbmc.log("Node: {0} - name: {1}, url: {2},  children: {3}".format(node.id, node.name, node.url, str(node.children)))
            node_set.remove(node)

        # Export tree to dict
        return root.to_dict(node_set)

def build_url(query):
    return PLUGIN_URL + '?' + urllib.urlencode(query)

#### Main script execution begins here on each load ####
PLUGIN_URL = sys.argv[0]
PLUGIN_HANDLE = int(sys.argv[1])
ARGS = urlparse.parse_qs(sys.argv[2][1:])

xbmcplugin.setContent(PLUGIN_HANDLE, 'episodes')

mode = ARGS.get('mode', None)

if mode == None:  # First load, generate course structure
    # init progress dialog
    progress = xbmcgui.DialogProgress()

    # setup client with access token
    progress.create('edX', "Asking server for access token...")
    client = EdxClient()
    client.get_access_token()

    # fetch list of courses
    progress.update(5, "Fetching course list...")
    courses = Course.build_from_results(client.get_courses())
    xbmc.log('edX course listing: ' + str(courses))

    # per course, build directory structure
    # simple progress calculation: get_access_token, get_courses, and each top-level addDirectoryItem are 1 'op'
    current_progress = 2  # get_access_token and get_courses
    max_progress = (2 + len(courses))
    for course in courses:
        progress.update(current_progress * 100 / max_progress, "Fetching course data for " + course.name)
        blocks, root_id = client.get_course_blocks(course.api_url)
        tree = course.build_tree(blocks, root_id)
        xbmc.log("******* tree:" + str(tree))
        # serialize that to settings, somehow
        # add top-level entry to current dir listing
        current_progress = current_progress + 1

    progress.close()
