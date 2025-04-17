
from . import vertex_groups
from . import shape_keys

def register():
    vertex_groups.register()
    shape_keys.register()

def unregister():
    vertex_groups.unregister()
    shape_keys.unregister()
