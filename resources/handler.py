"""
Main handler for plugin.video.edx
"""
import json
import urllib
import xbmc
import xbmcgui
import xbmcplugin

from resources.course import Course


def build_url(plugin_url, query):
    """
    Utility function for callbacks.
    """
    return plugin_url + '?' + urllib.urlencode(query)


def settings_error():
    """
    Show an error if required settings not present.
    """
    dialog = xbmcgui.Dialog()
    # i18n these strings!
    dialog.ok('edX Error', 'Error in edX configuration. Please ensure that username and password are valid. If you don\'t have an account, visit https://courses.edx.org/register to sign up and start learning!')


def file_location(key, extension=''):
    plugin_prefix = "plugin.video.edx"
    return "{0}{1}:{2}{3}".format(
        xbmc.translatePath('special://temp'),
        plugin_prefix,
        key,
        extension
    )


def write_tree(key, values):
    """
    Writes a course tree to temp storage, 1 layer at a time
    This allows for quick loading of submenus
    """
    values_to_write = []
    for val in values:
        if 'children' in val:
            values_to_write.append(
                {
                    'id': val['id'],
                    'name': val['name'],
                    'children': True
                }
            )
            write_tree(val['id'], val['children'])
        else:
            values_to_write.append(val)
            stream_file = file_location(key, '.strm')
            with open(stream_file, 'w+') as write_file:
                write_file.write(val['url'])
    with open(file_location(key), 'w+') as write_file:
        write_file.write(json.dumps(values_to_write))


def refresh_course_structure(client):
    """
    Refreshes the course structure stored on disk.

    Returns an id, name tuple for each of the top-level courses.
    """
    # init progress dialog
    progress = xbmcgui.DialogProgress()

    # setup client with access token
    progress.create('edX', "Asking server for access token...")
    client.get_access_token()

    # fetch list of courses
    progress.update(5, "Fetching course list...")
    courses = Course.build_from_results(client.get_courses())

    # simple progress: 1 op for get_access_token, get_courses, and each course
    current_progress = 2  # get_access_token and get_courses
    max_progress = (2 + len(courses))

    # per course, build directory structure
    ids = []
    for course in courses:
        progress.update(
            current_progress * 100 / max_progress,
            "Fetching course data for " + course.name
        )
        blocks, root_id = client.get_course_blocks(course.api_url)
        tree = course.build_tree(blocks, root_id)
        ids.append((tree['id'], tree['name']))

        # serialize
        write_tree(root_id, tree['children'])

        # update progress
        current_progress = current_progress + 1

    progress.close()
    return ids


def handle(mode, key, client, handle, base_url):
    """
    Main handling logic for plugin
    """
    if mode == None:  # First load
        courses = refresh_course_structure(client)

        # add top-level entries to current dir listing
        for c_id, c_name in courses:
            url = build_url(base_url, {'mode':'folder', 'cur_key': c_id})
            li = xbmcgui.ListItem(c_name)
            xbmcplugin.addDirectoryItem(
                handle=handle,
                url=url,
                listitem=li,
                isFolder=True
            )

        xbmcplugin.endOfDirectory(handle)

    elif mode[0] == 'folder':
        # We're in a folder
        folder_path = file_location(key[0])
        with open(folder_path, 'r') as read_file:
            values = json.loads(read_file.read())
        for val in values:
            if 'children' in val:
                url = build_url(base_url, {'mode':'folder', 'cur_key': val['id']})
                li = xbmcgui.ListItem(val['name'])
                xbmcplugin.addDirectoryItem(
                    handle=handle,
                    url=url,
                    listitem=li,
                    isFolder=True
                )
            else:
                li = xbmcgui.ListItem(val['name'])
                li.setProperty('IsPlayable', 'true')
                url = build_url(base_url, {'mode': 'play', 'cur_key': val['id']+'.strm'})
                xbmcplugin.addDirectoryItem(
                    handle=handle,
                    url=val['url'],
                    listitem=li,
                    isFolder=False
                )
        xbmcplugin.endOfDirectory(handle)

    elif mode[0] == 'play':
        play_item = xbmcgui.ListItem(path=key[0])
        xbmcplugin.setResolvedUrl(handle, True, listitem=play_item)
