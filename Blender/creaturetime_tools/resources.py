
import bpy
import os
from . import constants

_RESOURCES_DIR = os.path.join(constants.MAIN_DIR, "resources")
_MAIN_RESOURCES = 'main'

_RESOURCES = {}

def load_resources():
    # Note that preview collections returned by bpy.utils.previews
    # are regular py objects - you can use them to store custom data.
    import bpy.utils.previews
    pcoll = bpy.utils.previews.new()

    # load a preview thumbnail of a file and store in the previews collection
    for filename in os.listdir(_RESOURCES_DIR):
        name, ext = os.path.splitext(filename)
        if ext == ".png":
            pcoll.load(name, os.path.join(_RESOURCES_DIR, filename), 'IMAGE')

    _RESOURCES[_MAIN_RESOURCES] = pcoll

def unload_resources():
    for pcoll in _RESOURCES.values():
        bpy.utils.previews.remove(pcoll)
    _RESOURCES.clear()

def get(name):
    return _RESOURCES[_MAIN_RESOURCES][name]
