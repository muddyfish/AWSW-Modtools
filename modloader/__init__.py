"""This file is free software under the MIT license."""

#TODO - Modtools workshop item - fixed ID. Announcements to be made as metadata for that item. Show if changed?

import os
import sys
import renpy
try:
    from steam_workshop.steam_config import has_steam
    from steam_workshop.steamhandler import get_instance
    get_instance()
except (ImportError, OSError):
    workshop_enabled = False
    def has_steam():
        return False
else:
    workshop_enabled = True

from types import ModuleType
import importlib

print 'AWSW Mod Loader Init'


def get_mod_path():
    """Get the mod path

    Returns:
        The full path to the mods folder
    """
    return os.path.join(renpy.config.gamedir, "mods")


def report_exception(error):
    if has_steam():
        manager = get_instance()
        # Steam only uploads minidumps after 10 exceptions for some reason
        for i in range(11):
            manager.HandleException(error)


def get_platform_name():
    valid_paths = {"linux-i686", "linux-x86_64", "windows-i686", "darwin-x86_64"}
    for path in valid_paths:
        if any(path in i for i in sys.path):
            return path
    raise OSError("Modtools can't detect OS")

# Credit to Matthew for this code: https://stackoverflow.com/a/17194836/3398583
# Modified by Blue
def rreload(module, modules=None):
    """Recursively reloads a module.

    Ignores modules in ``modules`` and all modules not in the mods folder
    """
    print "RELOADING", module.__file__
    sys.stdout.flush()
    reload(module)
    if modules is None:
        modules = [module]
    else:
        modules.append(module)
    for attribute_name in dir(module):
        attribute = getattr(module, attribute_name)
        if isinstance(attribute, ModuleType):
            if attribute not in modules:
                try:
                    if get_mod_path() in attribute.__file__:
                        rreload(attribute, modules)
                except AttributeError:
                    # Seems to happen to sys randomly
                    pass


def is_github():
    return renpy.loader.loadable("github.txt")


def test_command():
    renpy.arguments.takes_no_arguments("Run internal modtools tests")

    import testing.test as test
    test.test_tests()

    return False


def update_command():
    from modloader.modconfig import update_modtools
    zip_default = "https://github.com/AWSW-Modding/AWSW-Modtools/archive/develop.zip"

    ap = renpy.arguments.ArgumentParser(description="Update the modtools.")
    ap.add_argument("url", help="The URL to get the new version from. Must be a zip file.", nargs='?', default=zip_default)
    args = ap.parse_args()

    update_modtools(args.url)


def main(reload_mods=False):
    """Load the mods"""
    # Don't want to do this at the top because it breaks initial parse error handling.
    from modloader import modinfo, modclass
    from modloader.modconfig import report_duplicate_labels

    #from steam_workshop.steam_config import sign_mod
    #sign_mod(1597292073)

    if reload_mods:
        import modgame
        rreload(modgame)

    report_duplicate_labels()

    if has_steam():
        steammgr = get_instance()
        steammgr.CachePersonas()

    # By appending the mod folder to the import path we can do something like
    # `import test` to import the mod named test in the mod folder.
    sys.path.append(get_mod_path())
    # NOTE: To import files in the modloader/ folder, do
    # `from modloader import ...`. If we add the modloader to the path,
    # the modules would be reimported every time they are imported.
    # In most cases, that's fine, but when modinfo is reimported, we lose the
    # current list of mods.

    # To run tests, do `python -O Angels with Scaly Wings.py . modtools_tests` in the AWSW root folder.
    # Otherwise `.` has to be the path to the AWSW directory


    renpy.arguments.register_command("modtools_tests", test_command)
    renpy.arguments.register_command("modtools_update", update_command)

    modinfo.reset_mods()

    modules = []
    for mod in os.listdir(get_mod_path()):
        if not os.path.isdir(os.path.join(get_mod_path(), mod)):
            raise EnvironmentError("The contents of the mods folder must all be folders.\n"
                                   "Zip files should be extracted into their own directory as in the core mod.\n"
                                   "{} is not a folder.\n"
                                   "If you click Remove Mod and Reload, all files in the mods folder will be removed."
                                   .format(mod))
        # Some mods require resources to be recognized by renpy.
        # If a folder exists, force renpy to load it
        resource_dir = os.path.join(get_mod_path(), mod, 'resource')
        if os.path.isdir(resource_dir):
            renpy.config.searchpath.append(resource_dir)

        print "Begin mod load: {}".format(mod)

        # Try importing the mod.
        # Note: This doesn't give my mod functionality. To give the mod
        # function, make a Mod class and apply the loadable_mod decorator
        mod_object = importlib.import_module(mod)
        if reload_mods:
            rreload(mod_object, modules)

    # After all mods are loaded, call their respective mod_complete functions
    for mod_name, mod in modinfo.get_mods().iteritems():
        print "Completing mod {}".format(mod_name)
        mod.mod_complete()

    # Force renpy to reindex all game files
    renpy.loader.old_config_archives = None


# When we build the documentation, renpy.config.gamedir will not exist
# However, when the game is ran, it will exist. We take abuse of that

try:
    game_dir = renpy.config.gamedir
    BUILDING_DOCUMENTATION = False
except AttributeError:
    BUILDING_DOCUMENTATION = True
else:
    sys.path.append(os.path.join(renpy.config.gamedir, "modloader", "dll", get_platform_name()))
    os.environ["SSL_CERT_FILE"] = os.path.join(game_dir, "modloader", "cacert.pem")
