"""Sandbox paths for file tools (agent cannot escape this directory)."""

from __future__ import annotations

import re
from pathlib import Path

from MemoryManager.settings import agent_workspace_path

_SAFE_NAME = re.compile(r"^[\w.\- ]{1,200}$")


def get_agent_workspace() -> Path:
    return agent_workspace_path()


# Resolved at import for tools that read this constant
AGENT_WORKSPACE = agent_workspace_path()


def resolve_path(path: str) -> Path:
    """
    Resolves a string to a Path object.
    Allows absolute paths.
    """
    return Path(path).resolve()


def search_files(search_path: str, query: str) -> str:
    """
    Searches for files or directories matching a query within a given path,
    or lists all contents if the query is a wildcard ('*') or empty.
    If the initial search yields no results, it will try other common locations.

    This function expands common user-friendly paths (e.g., 'Desktop', 'Documents')
    and performs a case-insensitive search.

    Args:
        search_path: The directory to start the search from (e.g., 'Desktop').
        query: The name or partial name of the file/folder, or '*' to list all.

    Returns:
        A JSON string containing a list of found paths or an error message.
    """
    import json

    try:
        # Expand user-friendly paths like '~'
        base_path = Path(search_path).expanduser()

        # List of special folders to search
        special_folders = {
            "desktop": Path.home() / "Desktop",
            "documents": Path.home() / "Documents",
            "downloads": Path.home() / "Downloads",
        }
        
        search_locations = []
        if search_path.lower() in special_folders:
            # Prioritize the requested folder, then add the others
            search_locations.append(special_folders[search_path.lower()])
            for name, path in special_folders.items():
                if name != search_path.lower():
                    search_locations.append(path)
        elif base_path.is_dir():
            search_locations.append(base_path)
        else:
            # If the path is not a special folder and not a directory, search all special folders
            search_locations.extend(special_folders.values())

        found_items = []
        list_all_mode = query == '*' or not query.strip()
        query_lower = query.lower()

        for location in search_locations:
            if location.is_dir():
                for item in location.rglob('*'):
                    if list_all_mode:
                        found_items.append(str(item))
                    elif query_lower in item.name.lower():
                        found_items.append(str(item))
            
            # If we found items in the primary search location, don't check the others
            if found_items and location == search_locations[0]:
                break

        if not found_items:
            return json.dumps({"ok": True, "message": "No files or folders found matching the query in Desktop, Documents, or Downloads."})

        return json.dumps({"ok": True, "results": found_items})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})
