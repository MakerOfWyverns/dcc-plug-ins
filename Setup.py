import os
import shutil

ROOT_DIR = os.path.dirname(__file__)

BLENDER_PLUGINS_DIR = os.path.join(ROOT_DIR, 'Blender')

CREATURETIME_PLUGIN_STUB = '.creaturetime-plugin'

def generate_zip_files():
    to_zip = []
    delete_files = []
    for filename in os.listdir(BLENDER_PLUGINS_DIR):
        filepath = os.path.join(BLENDER_PLUGINS_DIR, filename)
        if os.path.isdir(filepath):
            creature_time_stub = os.path.join(filepath, CREATURETIME_PLUGIN_STUB)
            if not os.path.isfile(creature_time_stub):
                with open(creature_time_stub, 'w') as _:
                    pass
            to_zip.append(filepath)
        else:
            delete_files.append(filepath)

    for f in delete_files:
        os.remove(f)

    zip_files = []
    for fp in to_zip:
        zip_files.append(shutil.make_archive(fp, 'zip', fp))

    return zip_files

def unpack_zip_files(zip_files):
    # TODO: Find all installed blender versions.
    version = '4.4'
    extensions_dir = f'%APPDATA%/Blender Foundation/Blender/{version}/extensions/user_default'
    extensions_dir = os.path.expandvars(extensions_dir)
    if not os.path.isdir(extensions_dir):
        os.makedirs(extensions_dir)

    # Remove existing extensions.
    for filename in os.listdir(extensions_dir):
        filepath = os.path.join(extensions_dir, filename)
        if os.path.isdir(filepath):
            stub_file = os.path.join(filepath, CREATURETIME_PLUGIN_STUB)
            if os.path.isfile(stub_file):
                shutil.rmtree(filepath)

    for src in zip_files:
        dst = os.path.join(extensions_dir, os.path.basename(src))
        shutil.unpack_archive(src, os.path.splitext(dst)[0], 'zip')

if __name__ == '__main__':
    zipFiles = generate_zip_files()
    unpack_zip_files(zipFiles)