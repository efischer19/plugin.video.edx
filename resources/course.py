"""
This module contains all the logic used to translate the results of a
course_blocks api call into a plugin-useable dictionary of videos and
folders that contain videos.
"""

def youtube_url(initial_url):
    """
    Utility function to build a YouTube url playable by Kodi.

    See http://kodi.wiki/view/Add-on:YouTube for details.
    """
    video_id = initial_url.split('=')[1]
    return 'plugin://plugin.video.youtube/?path=/root/video&action=play_video&videoid={0}'.format(
        video_id
    )


class NodeDefaultDict(dict):  # pylint: disable=too-few-public-methods
    """
    A defaultdict that takes a key argument, and creates a new Node if missing
    """
    def __missing__(self, key):
        ret = self[key] = Node(key)
        return ret


class Course(object):
    """
    Contains all the relevant info for the user's courses
    """

    def __init__(self, name, number, org, api_url):
        """
        name: string - used as directory title
        number: string
        org: string
        api_url: the api to be used for further api requests for this course
        """
        self.name = name
        self.number = number
        self.org = org
        self.api_url = api_url

    def __repr__(self):
        return "{0} {1}: {2}".format(self.org, self.number, self.name)

    @classmethod
    def build_from_results(cls, results):
        """
        Builds and returns a list of Course objects, given a course listing result.
        """
        return [
            Course(r['name'], r['number'], r['org'], r['blocks_url'])
            for r in results
        ]

    def build_tree(self, blocks, root_id):  # pylint: disable=no-self-use
        """
        Builds and returns a dict representing the tree for this course
        """
        nodes = NodeDefaultDict()

        # Build Node objects
        for key, value in blocks.iteritems():
            node = nodes[key]
            node.name = value['display_name']
            try:
                if value['type'] != 'video':
                    node.children = [
                        nodes[child_id]
                        for child_id in value['children']
                    ]
                else:
                    urls = []
                    videos_dict = value['student_view_data']['encoded_videos']
                    for key, val in videos_dict.iteritems():
                        if key == 'youtube':
                            urls.append(youtube_url(val['url']))
                        else:
                            urls.append(val['url'])
                    node.url = urls.pop(0)
                    node.alternate_urls = urls
            except KeyError:
                pass  # if something went wrong, either:
                        # we won't be able to play this video node, or
                        # this non-video node has no children

        # Prune invalid paths (branches with no video)
        root = nodes[root_id]
        root.pruning_walk()

        # Export tree to dict
        return root.to_dict()


class Node(object):
    """
    Used to build a linked list DAG of the course tree
    """
    def __init__(self, key):
        self.children = set()
        self.name = ''
        self.url = ''
        self.alternate_urls = []
        self._id = key
        self.should_prune = True

    def is_leaf(self):  # pylint: disable=missing-docstring
        return len(self.children) == 0

    def pruning_walk(self):
        """
        Recursively traverses the course tree, and marks video leaf nodes and
        their ancestors for keeping. Other nodes are marked to be removed.
        """
        if self.is_leaf():
            if self.url:
                self.should_prune = False
        else:
            for child in self.children:
                if not child.pruning_walk():
                    self.should_prune = False
                else:
                    self.children.remove(child)
        return self.should_prune

    def to_dict(self):
        """
        Recursively traverses the course tree to build a dictionary of useful
        items, for serialization by the plugin.
        """
        if self.is_leaf():
            ret_dict = {
                'id': self._id,
                'name': self.name,
                'url': self.url
            }
            # Alternate urls are not used at all right now, but they exist
            if self.alternate_urls:
                ret_dict['alternate_urls'] = self.alternate_urls
            return ret_dict

        # This is not a leaf node, and will have child dictionaries
        return {
            'id': self._id,
            'name': self.name,
            'children': [
                node.to_dict()
                for node in self.children
            ]
        }
