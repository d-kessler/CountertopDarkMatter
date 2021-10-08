from shutil import rmtree
import os

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir(os.path.join(".."))


def get_file_names(folder_path, extensions=None):
    """
    Returns the names of all files located in 'folder_path', restricts the list to file with the extensions passed
    (if any extensions were passed); if 'extensions' equals 'images', all image files are returned.
    """
    if extensions == "images":
        extensions = [".jpeg", ".jpg", ".png", ".gif", ".heic", ".heif"]
    if extensions:
        return [f.name for f in os.scandir(folder_path)
                if os.path.splitext(f.name)[-1] in extensions]
    else:
        return [f.name for f in os.scandir(folder_path)]


def get_extension(path):
    """
    Returns the extension of the file located at 'path', '.' included.
    """
    return os.path.splitext(path)[-1]


def get_subfolder_names(folder_path):
    """
    Returns the names of all subfolders in 'folder_path'.
    """
    return [f.name for f in os.scandir(folder_path) if f.is_dir()]


def remove_file(path):
    """
    Removes the file located at 'path' if it exists.
    """
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def clear_folder(folder_path):
    """
    Clears (deletes) the contents of 'folder_path', without deleting the directory.
    """
    try:
        rmtree(folder_path)
        os.mkdir(folder_path)
    except PermissionError:
        input(f"\nPermissions error for {folder_path}. "
              f"Exit the directory and all files open in the directory, then press enter to continue: ")
        clear_folder(folder_path)


def make_folder(folder_path, clear_existing=True):
    """
    Makes a folder at the given directory 'folder_path'. If 'clear_existing' equals True, any existing folder at the
    same directory is deleted.
    """
    if not os.path.exists(folder_path):
        os.mkdir(folder_path)
    else:
        if clear_existing is True:
            clear_folder(folder_path)
