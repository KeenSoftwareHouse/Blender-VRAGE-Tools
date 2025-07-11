import bpy
import sys
import re
import json
import time
import requests
import webbrowser

from bpy.types              import Operator
from bpy.props              import BoolProperty

from ..preferences          import get_preferences


rel_ver = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+$")
dev_ver = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+\-\w+\.[0-9]{1,}$")

git_url = "https://github.com/KeenSoftwareHouse/Blender-VRAGE-Tools"


class VRT_OT_GetCurrentVersion(Operator):
    """Opens the webpage of the latest release"""
    bl_idname = "wm.vrt_get_current_version"
    bl_label = "Get Current Version"
    bl_options = {'REGISTER', 'UNDO'}

    releases: BoolProperty()

    def execute(self, context):

        preferences = get_preferences()

        if preferences.addon_latest_version == "" or self.releases:
            webbrowser.open(f"{git_url}/releases/")
        else:
            webbrowser.open(f"{git_url}/releases/tag/v{preferences.addon_latest_version}")

        return {'FINISHED'}


class VRT_OT_CheckUpdate(Operator):
    """Check whether a newer update is available"""
    bl_idname = "wm.vrt_check_update"
    bl_label = "Check for Updates"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):

        addon = sys.modules["vrage_tools"]
        preferences = get_preferences()

        preferences.addon_current_version = str(addon.bl_info['version'])[1:-1].replace(', ', '.')

        check_repo_update(force=True)

        return {'FINISHED'}


def check_repo_update(force=False):
    """Checks the GitHub API for the latest release of the repository."""

    preferences = get_preferences()
    preferences.addon_needs_update = False
    preferences.addon_update_message = ""

    user_reponame = git_url[len("https://github.com/"):]
    url_tags = f"https://api.github.com/repos/{user_reponame}/tags"
    url_releases = f"https://api.github.com/repos/{user_reponame}/releases"
    current_version = tuple(map(int, preferences.addon_current_version.split('.')))

    try:
        skip = False
        if time.time() - preferences.addon_last_check >= 4000 or force:
            response_tags = requests.get(url_tags)
            response_releases = requests.get(url_releases)
            json_tags = response_tags.json()
            json_releases = response_releases.json()

            if response_tags.status_code == 200 and response_releases.status_code == 200:
                preferences.addon_cache_tags = json.dumps(json_tags)
                preferences.addon_cache_releases = json.dumps(json_releases)
                preferences.addon_last_check = time.time()

        else:
            json_tags = json.loads(preferences.addon_cache_tags)
            json_releases = json.loads(preferences.addon_cache_releases)
            skip = True

        if skip or (response_tags.status_code == 200 and response_releases.status_code == 200):
            versions = list()

            for tag in json_tags:
                name_tag = tag['name']

                for release in json_releases:
                    name_release = release['tag_name']

                    if name_tag == name_release:
                        if rel_ver.match(name_tag):
                            versions.append(name_tag)
                        break

            if versions == []:
                preferences.addon_update_message = "No valid releases found."
                return

            latest_version_name = sorted(versions, reverse=True)[0][1:]
            latest_version = tuple(map(int, latest_version_name.split('.')))

            current_version = tuple(current_version)
            preferences.addon_latest_version = latest_version_name

            if current_version < latest_version:
                if current_version == (0, 0, 0):
                    outdated = f"VRAGE Tools not installed."
                else:
                    outdated = f"VRAGE Tools version {latest_version_name} available!"
                preferences.addon_update_message = outdated
                preferences.addon_needs_update = True

            elif current_version > latest_version:
                preferences.addon_update_message = "Latest development version."
                preferences.addon_needs_update = False

            else:
                preferences.addon_update_message = f"VRAGE Tools is up to date."
                preferences.addon_needs_update = False

        elif response_tags.status_code == 403 or response_releases.status_code == 403:
            preferences.addon_update_message = "Rate limit exceeded! Please wait one hour to check again."

        else:
            preferences.addon_update_message = "No valid releases found."

    except Exception as e:
        print(e)
        preferences.addon_update_message = "Connection Failed!"
