import json
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

class EdxClient(object):
    """
    A class containing all the "talk to edx servers" functionality needed by this plugin.
    """

    def __init__(self):
        self.access_token_url = BASE_URL + 'oauth2/access_token/'
        __access_token = ''

    def get_access_token(self):
        """
        Uses class constants (eventually settings values) to get an access token
        """
        response = requests.post(
            self.access_token_url,
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
        data = self.get_response_data(url)
        return data['results']

    def get_course_blocks(self, base_course_url):
        # url is constructed to get all video blocks, as well as all structure blocks
        url = base_course_url + "&username=" + USERNAME + "&depth=all&block_types_filter=video,course,chapter,sequential,vertical&requested_fields=children&student_view_data=video"
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
                self.alternate_urls = []
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
                    ret_dict = {
                        'id': self.id,
                        'name': self.name,
                        'url': self.url
                    }
                    if self.alternate_urls:
                        ret_dict['alternate_urls'] = self.alternate_urls
                    return ret_dict
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
                    urls = []
                    for key, val in value['student_view_data']['encoded_videos'].iteritems():
                        if key == 'youtube':
                            # youtube url has format "https://www.youtube.com/watch?v=$VIDEOID"
                            # we want "plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=$VIDEOID"
                            # per http://kodi.wiki/view/Add-on:YouTube
                            video_id = val['url'].split('=')[1]
                            urls.append('plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid=' + video_id)
                        else:
                            urls.append(val['url'])
                    node.url = urls.pop(0)
                    node.alternate_urls = urls
            except KeyError:
                pass  # if something went wrong, we won't be able to play this video node, or the non-video node has no children
            node_set.add(node)

        # Prune invalid paths (branches with no video)
        root = next(node for node in node_set if node.id == root_id)
        root.pruning_walk(node_set)
        for node in [node for node in node_set if node.should_prune]:
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
current_key = ARGS.get('cur_key', None)
BASE_URL = xbmcplugin.getSetting(PLUGIN_HANDLE, 'base_url')
USERNAME = xbmcplugin.getSetting(PLUGIN_HANDLE, 'username')
USER_PASSWORD = xbmcplugin.getSetting(PLUGIN_HANDLE, 'password')
OAUTH2_CLIENT_ID = 'plugin.video.edx.hackathon_dev_id'

if not BASE_URL or not USERNAME or not USER_PASSWORD:
    dialog = xbmcgui.Dialog()
    # i18n these strings!
    dialog.ok('edX Error', 'Error in edX configuration. Please ensure that username and password are valid. If you don\'t have an account, visit https://courses.edx.org/register to sign up and start learning!')
else:
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

        # simple progress calculation: get_access_token, get_courses, and each top-level addDirectoryItem are 1 'op'
        current_progress = 2  # get_access_token and get_courses
        max_progress = (2 + len(courses))

        # per course, build directory structure
        for course in courses:
            progress.update(current_progress * 100 / max_progress, "Fetching course data for " + course.name)
            blocks, root_id = client.get_course_blocks(course.api_url)
            tree = course.build_tree(blocks, root_id)

            # serialize
            def write_tree(key, values):
                # id for children if they have children
                # else, full value
                values_to_write = []
                for val in values:
                    if 'children' in val:
                        values_to_write.append({'id': val['id'], 'name': val['name'], 'children': True})
                        write_tree(val['id'], val['children'])
                    else:
                        values_to_write.append(val)
                        with open(xbmc.translatePath('special://temp')+key+'.strm', 'w+') as file:
                            file.write(val['url'])
                with open(xbmc.translatePath('special://temp')+key, 'w+') as file:
                    file.write(json.dumps(values_to_write))

            write_tree(root_id, tree['children'])

            # add top-level entry to current dir listing
            url = build_url({'mode':'folder', 'cur_key': tree['id']})
            li = xbmcgui.ListItem(tree['name'])
            xbmcplugin.addDirectoryItem(handle=PLUGIN_HANDLE, url=url, listitem=li, isFolder=True)

            # update progress
            current_progress = current_progress + 1

        progress.close()
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

    elif mode[0] == 'folder':
        # We're in a folder
        with open(xbmc.translatePath('special://temp')+current_key[0], 'r') as file:
            values = json.loads(file.read())
        for val in values:
            if 'children' in val:
                url = build_url({'mode':'folder', 'cur_key': val['id']})
                li = xbmcgui.ListItem(val['name'])
                xbmcplugin.addDirectoryItem(handle=PLUGIN_HANDLE, url=url, listitem=li, isFolder=True)
            else:
                li = xbmcgui.ListItem(val['name'])
                li.setProperty('IsPlayable', 'true')
                url = build_url({'mode': 'play', 'video': val['id']+'.strm'})
                xbmcplugin.addDirectoryItem(handle=PLUGIN_HANDLE, url=val['url'], listitem=li, isFolder=False)
        xbmcplugin.endOfDirectory(PLUGIN_HANDLE)

    elif mode[0] == 'play':
        play_item = xbmcgui.ListItem(path=ARGS['video'])
        xbmcplugin.setResolvedUrl(PLUGIN_HANDLE, True, listitem=play_item)
