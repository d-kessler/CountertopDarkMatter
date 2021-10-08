import os
from shutil import copyfile
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

from python.utils.csv_excel_utils import CsvUtils, ExcelUtils, get_name_id_dict
from python.utils.file_utils import make_folder, get_file_names, get_subfolder_names

from python.vars.paths_and_ids import experiment_folder_drive_id, simulation_folder_drive_id, \
    negative_folder_drive_id, marking_folder_drive_id, manifests_folder_drive_id, \
    manifests_csv_folder_drive_id, repository_folder_drive_id, \
    staging_ground_folder_drive_id, name_id_manifest_path, name_id_manifest_csv_path, \
    unprocessed_images_zeroth_folder, fetched_images_folder, experiment_subjects_folder

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir("..")


def get_file_root(file_name, top_dir='..' + os.path.sep):
    for root, dirs, files in os.walk(top_dir):
        for file in files:
            if file == file_name:
                return os.path.abspath(root)


class GoogleDriveUtils:
    # Storing here for convenient reference
    experiment_folder_id = experiment_folder_drive_id
    simulation_folder_id = simulation_folder_drive_id
    negative_folder_id = negative_folder_drive_id
    marking_folder_id = marking_folder_drive_id
    manifests_folder_id = manifests_folder_drive_id
    manifests_csv_folder_id = manifests_csv_folder_drive_id

    gfolder_mime_type = 'application/vnd.google-apps.folder'

    def __init__(self):
        # Ensuring that the current working direction contains 'settings.yaml' (necessary for authentication)
        self.configure()
        # Authenticating with Google Drive, getting an instance of GoogleDrive
        self.drive = self.get_drive()

    @staticmethod
    def configure(settings_file_name="settings.yaml"):
        """
        Ensures that the current working direction contains 'settings.yaml' (necessary for authentication)
        """
        settings_root = get_file_root(settings_file_name)
        os.chdir(settings_root)

    @staticmethod
    def get_drive(credentials_file_name="google_drive_credentials.txt"):
        """
        Authenticates with Google Drive using 'google_drive_credentials.txt', returns an instance of GoogleDrive.
        """
        gauth = GoogleAuth()
        # Try to load saved client credentials
        gauth.LoadCredentialsFile(credentials_file_name)
        if gauth.credentials is None:
            # Authenticate if they're not there
            gauth.GetFlow()
            gauth.flow.params.update({'access_type': 'offline'})
            gauth.flow.params.update({'approval_prompt': 'force'})
            gauth.LocalWebserverAuth()
        elif gauth.access_token_expired:
            # Refresh them if expired
            gauth.Refresh()
        else:
            # Initialize the saved credentials
            gauth.Authorize()
        # Save the current credentials to a file
        gauth.SaveCredentialsFile(credentials_file_name)
        drive = GoogleDrive(gauth)
        return drive

    def download_from_staging_ground(self):
        """
        Downloads the contents of the 'Image Processing Staging Ground' Google Drive folder to 'unprocessed_images_zeroth_folder'.
        """
        first_gfolders = self.get_subgfolders(staging_ground_folder_drive_id)
        for first_gfolder in first_gfolders:
            print(f"Entering into {first_gfolder['title']}...")
            first_folder_local_path = \
                os.path.join(unprocessed_images_zeroth_folder, first_gfolder['title'])
            make_folder(first_folder_local_path, clear_existing=False)
            second_gfolders = self.get_subgfolders(first_gfolder['id'])
            for second_gfolder in second_gfolders:
                if not second_gfolder['title'][0].isnumeric() \
                        and second_gfolder['title'].split('_')[0][0] != "u":  # Ignoring non-slab folders
                    continue
                second_folder_local_path = \
                    os.path.join(first_folder_local_path, second_gfolder['title'])
                make_folder(second_folder_local_path, clear_existing=False)
                print(f"\tDownloading {second_gfolder['title']}... ")
                self.download_gfolder(second_gfolder['id'], second_folder_local_path)
        print("Images downloaded.")

    def get_subgfolders(self, drive_folder_id):
        """
        Returns a list of gfile instances for the subfolders in the Google Drive folder with ID 'drive_folder_id'.
        """
        return self.list_gfiles(drive_folder_id, mime_types=[self.gfolder_mime_type])

    def list_gfiles(self, gfolder_id, mime_types=None, exclude_mime_types=None):
        """
        Returns a list of gfile instances for the files/folders in the Google Drive folder with ID 'drive_folder_id'.
            mime_types = mime types to be included in the list
            exclude_mime_types = mime types to be excluded from the list
        """
        if mime_types is None:
            mime_types = []
        if exclude_mime_types is None:
            exclude_mime_types = []
        all_gfiles = self.drive.ListFile({'q': f"'{gfolder_id}' in parents and trashed=false"}).GetList()
        if mime_types:
            return [gfile for gfile in all_gfiles if gfile['mimeType'] in mime_types]
        elif exclude_mime_types:
            return [gfile for gfile in all_gfiles if gfile['mimeType'] not in exclude_mime_types]
        return all_gfiles

    def download_gfolder(self, gfolder_id, destination_folder_path, append_to_existing=False):
        """
        Downloads the contents of the Google Drive folder with ID 'gfolder_id' to the local 'destination_folder_path'.
            append_to_existing = True to download files already found in destination_folder_path
        """
        local_file_names = get_file_names(destination_folder_path)
        gfile_list = self.list_gfiles(gfolder_id)
        for gfile in gfile_list:
            if gfile['mimeType'] == self.gfolder_mime_type:
                self.download_gfolder(gfile['id'], destination_folder_path)
            elif not gfile['mimeType'].startswith('application/'):
                if gfile['title'] in local_file_names and append_to_existing is False:
                    continue
                destination_file_path = \
                    os.path.join(destination_folder_path, gfile['title'])
                self.download_gfile(gfile['id'], destination_file_path)
            else:
                print(f"Unsupported file: {gfile['title']}")

    def download_gfile(self, gfile_id, destination_file_path):
        """
        Download the Google Drive file with ID 'gfile_id' to the local 'destination_file_path'.
        """
        gfile = self.drive.CreateFile({'id': gfile_id})
        gfile.GetContentFile(destination_file_path)

    def update_Name_ID_Manifest(self):
        """
        Update NameID_Manifest.xlsx with the contents of the 'Image Processing Staging Ground' Google Drive Folder
        """
        gfile_name_id_dict = self.get_gfile_name_id_dict(staging_ground_folder_drive_id)
        gfile_name_id_list = list(zip(gfile_name_id_dict.keys(), gfile_name_id_dict.values()))
        ExcelUtils(name_id_manifest_path).write_rows(gfile_name_id_list)
        CsvUtils(name_id_manifest_csv_path).write_rows(gfile_name_id_list)

    def get_gfile_name_id_dict(self, gfolder_id, gfile_name_id_dict=None):
        """
        From the files in the Google Drive folder with ID 'gfolder_id', create a dictionary with key-value pairs:
            '(file name)': (Google Drive file ID)
        """
        if gfile_name_id_dict is None:
            gfile_name_id_dict = {}
        gfile_list = self.list_gfiles(gfolder_id)
        for gfile in gfile_list:
            gfile_name_id_dict[str(gfile['title'])] = gfile['id']
            if gfile['mimeType'] == self.gfolder_mime_type:
                self.get_gfile_name_id_dict(gfile['id'], gfile_name_id_dict)
        return gfile_name_id_dict

    def upload_folder(self, local_folder_path, drive_folder_id, replace_existing=False):
        """
        Uploads the contents of 'local_folder_path' to the Google Drive folder with ID 'drive_folder_id'.
            replace_existing = True to replace files already found in 'drive_folder_id'
        """
        local_folder_image_names = get_file_names(local_folder_path)
        existing_gfile_names = [gfile['title'] for gfile in self.list_gfiles(drive_folder_id)]
        for local_folder_image_name in local_folder_image_names:
            if local_folder_image_name in existing_gfile_names and replace_existing is False:
                # Ignore images already in the drive folder
                continue
            local_folder_image_path = os.path.join(local_folder_path, local_folder_image_name)
            self.upload_file(local_folder_image_path, drive_folder_id, replace_existing)

    def upload_file(self, local_file_path, drive_folder_id, replace_existing=False):
        """
        Uploads the local file located at 'local_file_path' to the Google Drive folder with ID 'drive_folder_id'.
            replace_existing = True to replace the file if it is already found in 'drive_folder_id'
        """
        if replace_existing is True:
            gfiles = self.list_gfiles(drive_folder_id)
            for gfile in gfiles:
                if gfile['title'] == os.path.basename(local_file_path):
                    gfile.Trash()
        parents_metadata = [{'id': drive_folder_id}]
        drive_file = self.drive.CreateFile({'parents': parents_metadata})
        drive_file['title'] = os.path.basename(local_file_path)
        drive_file.SetContentFile(local_file_path)
        drive_file.Upload()

    def move_staging_ground_to_repository(self):
        """
        Moves the contents of 'Image Processing Staging Ground' to 'Slab Photos Repository'
        """
        gfolders = self.get_subgfolders(staging_ground_folder_drive_id)
        for gfolder in gfolders:
            self.move_gfile(gfolder, repository_folder_drive_id)

    @staticmethod
    def move_gfile(gfile, destination_gfolder_id):
        """
        Moves the file corresponding to the gfile instance 'gfile' to the Google Drive folder with ID 'drive_folder_id'.
        """
        gfile['parents'] = [{"kind": "drive#parentReference", "id": destination_gfolder_id}]
        gfile.Upload()

    def get_gfile_instance(self, parent_gfolder_id, gfile_id=None, gfile_name=None, mime_type=None):
        """
        Gets the gfile instance of a wanted file given 'parent_gfolder_id', the ID of its parent Google drive file,
        and either its Google Drive ID or name
        """
        gfiles = self.list_gfiles(parent_gfolder_id, mime_types=mime_type)
        for gfile in gfiles:
            if (gfile_id and gfile['id'] == gfile_id) or (gfile_name and gfile['title'] == gfile_name):
                return gfile

    def create_gfolder(self, gfolder_name, parent_gfolder_id):
        """
        Creates a subfolder named 'gfolder_name' in the Google Drive folder with ID 'parent_gfolder_id'.
        """
        gfile_list = self.list_gfiles(parent_gfolder_id)
        for gfile in gfile_list:
            if gfile['title'] == gfolder_name:
                return gfile
        gfolder = self.drive.CreateFile(
            {'title': gfolder_name,
             'parents': [{'id': parent_gfolder_id}],
             'mimeType': self.gfolder_mime_type})
        gfolder.Upload()
        return gfolder

    def download_gfile_by_name(self, file_name, destination_folder_path):
        """
        Attempts to download the Google Drive file with name 'file_name' to the local 'destination_folder_path'.
        (Only possible if the file was previously uploaded to 'Image Processing Staging Ground')
        """
        name_id_dict = get_name_id_dict()
        gfile_id = name_id_dict[file_name]
        destination_file_path = os.path.join(destination_folder_path, file_name)
        self.download_gfile(gfile_id, destination_file_path)

    def download_gfiles_by_name(self, file_names_list, destination_folder_path, replace_existing=False):
        """
        Analogue of 'download_gfile_by_name' for a list of file names.
            replace_existing = True to replace the file if it is already found in 'destination_folder_path'
        """
        local_file_names = get_file_names(destination_folder_path)
        name_id_dict = get_name_id_dict()
        downloaded_gfiles_ids = []
        for file_name in file_names_list:
            if file_name in local_file_names and replace_existing is True:
                continue
            gfile_id = name_id_dict[file_name]
            if gfile_id in downloaded_gfiles_ids:
                continue
            destination_file_path = os.path.join(destination_folder_path, file_name)
            self.download_gfile(gfile_id, destination_file_path)
            downloaded_gfiles_ids.append(gfile_id)

    def fetch_needed_images(self, needed_image_names, search_second_folders=False, search_experiment_folder=False):
        """
        Adds all needed images to `fetched_images_folder'. Fetching local images where possible;
        downloading images from Google Drive if need be.
            needed_image_names = list of the names of images that must be on the local machine
            search_second_folders = True to search the second folders within data/images
            search_experiment_folder = True to search process_data/experiment_images
        """
        images_already_fetched = get_file_names(fetched_images_folder, extensions="images")
        local_image_names = []
        local_image_paths = []
        if search_second_folders is True:
            for first_folder in get_subfolder_names(unprocessed_images_zeroth_folder):
                first_folder_path = os.path.join(unprocessed_images_zeroth_folder, first_folder)
                for second_folder in get_subfolder_names(first_folder_path):
                    second_folder_path = os.path.join(first_folder_path, second_folder)
                    image_names = get_file_names(second_folder_path, extensions="images")
                    image_paths = [os.path.join(second_folder_path, image_name) for image_name in image_names]
                    local_image_names.extend(image_names)
                    local_image_paths.extend(image_paths)
        if search_experiment_folder is True:
            image_names = get_file_names(experiment_subjects_folder, extensions="images")
            image_paths = [os.path.join(experiment_subjects_folder, image_name) for image_name in image_names]
            local_image_names.extend(image_names)
            local_image_paths.extend(image_paths)
        for name, path in zip(local_image_names, local_image_paths):
            if name in needed_image_names:
                if name in images_already_fetched:
                    continue
                copyfile(path, os.path.join(fetched_images_folder, name))
        images_to_download = [n for n in needed_image_names
                              if n not in local_image_names
                              and n not in images_already_fetched]
        self.download_gfiles_by_name(images_to_download, fetched_images_folder)
