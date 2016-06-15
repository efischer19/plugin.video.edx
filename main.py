import xbmcaddon
import xbmcgui

name = xbmcaddon.Addon().getAddonInfo('name')

xbmcgui.Dialog().ok(name, "Hello, World!")
