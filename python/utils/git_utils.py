import os
import sys
from git import Repo

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir(os.path.join(".."))


def push_files_to_GitHub(file_paths_to_push, commit_message=None, force_push=False):
    """
    IMPORTANT REMARK: File paths must be relative to "CountertopDarkMatter".
    """
    if commit_message is None:
        commit_message = f"upload {file_paths_to_push}"
    repo_directory = "."
    repo = Repo(repo_directory)
    repo.index.add(file_paths_to_push)
    repo.index.commit(commit_message)
    origin = repo.remote('origin')
    origin.push(force=force_push)
