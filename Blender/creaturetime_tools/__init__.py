from . import resources
from . import operators

def register():
    resources.load_resources()
    operators.register()


def unregister():
    operators.unregister()
    resources.unload_resources()
