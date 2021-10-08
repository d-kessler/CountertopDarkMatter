import os
from shutil import copyfile

from python.utils.git_utils import push_files_to_GitHub
from python.utils.zooniverse_utils import upload_subjects_to_zooniverse
from python.utils.csv_excel_utils import CsvUtils, ExcelUtils
from python.google_drive_folder.google_drive import GoogleDriveUtils

from python.vars.fieldnames import negative_fieldnames
from python.vars.project_info import negative_subject_set_id, negative_feedback_id
from python.vars.paths_and_ids import cleaned_classifications_manifest_csv_path, negative_csv_path, \
    negative_manifest_path, negative_manifest_csv_path, manifests_csv_folder_drive_id, \
    manifests_folder_drive_id, fetched_images_folder, negative_subjects_folder, negative_folder_drive_id

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir("..")


# TODO: Implement updated criteria


class CreateNegatives:

    def __init__(self, swap):
        self.subjects = list(swap.subjects.values())
        self.negative_csv = CsvUtils(negative_csv_path)
        self.negative_manifest = ExcelUtils(negative_manifest_path, negative_fieldnames)
        self.negative_manifest_csv = CsvUtils(negative_manifest_csv_path, negative_fieldnames)
        self.cleaned_classifications_csv = CsvUtils(cleaned_classifications_manifest_csv_path, negative_fieldnames)
        self.gd = GoogleDriveUtils()

    def run(self):
        """
        Getting a list of (k)SWAP subject instances that were retired as negative (upon their 'cumulative
        false-negatives' falling below the retirement threshold defined in 'analyze_and_promote').
        """
        negative_subjects = self.get_negative_subjects()
        """
        Getting a list of negative subjects' metadata dictionaries, created using information from (k)SWAP instances,
        'Negative_Manifest.xlsx', and 'cleaned_classifications.csv'.
        """
        negative_subjects_metadata_dicts = self.get_negative_subjects_metadata_dicts(negative_subjects)
        """
        Fetching (moving to the 'fetched_images' folder) all "negative-qualified" experiment images
        """
        self.gd.fetch_needed_images([d['#exp_file_name'] for d in negative_subjects_metadata_dicts],
                                    search_experiment_folder=True)
        """
        Copying negative-qualified experiment images from the 'fetched_images' folder to the  'negative_images' folder,  
        renaming appropriately.
        """
        self.copy_rename_negative_images(negative_subjects_metadata_dicts)
        """
        Writing negative images' metadata into 'negative_subjects.csv', 'Negative_Manifest.xlsx, 
        and 'Negative_Manifest.csv' (the backup manifest).
        """
        self.write_metadata(negative_subjects_metadata_dicts)
        """
        Uploading negative images to Zooniverse and Google Drive, and manifests to Google Drive and Github
        """
        self.upload()

    def get_negative_subjects(self):
        """
        Returns a list of (k)SWAP 'Subject' instances that were retired as 0 <-> 'Negative'.
        """
        return [s for s in self.subjects if s.retired_as == 0]

    def get_negative_subjects_metadata_dicts(self, negative_subjects):
        """
        Returns a list of dictionaries whose 'keys' are 'negative_fieldnames',
        each corresponding to a subject identified as 'Negative' by (k)SWAP.
            negative_subjects: list of (k)SWAP 'Subject' instances that were retired as 'Negative'
        """
        negative_subjects_metadata_dicts = []
        neg_i = self.negative_manifest.get_first_empty_row() - 1
        for neg_i, negative_subject in enumerate(negative_subjects, start=neg_i):
            negative_subject_id = 'n' + str(neg_i)
            cleaned_classification_row = self.cleaned_classifications_csv.find_row(
                identifier=negative_subject.subject_id,
                column_header='subject_znv_id')
            experiment_file_name = cleaned_classification_row['#file_name']
            negative_file_name = negative_subject_id + '_' + experiment_file_name
            negative_subjects_metadata_dicts.append({
                '!subject_id': negative_subject_id,
                '#file_name': negative_file_name,
                '#exp_file_name': experiment_file_name,
                '#cumulative_fnr': round(negative_subject.cumulative_fnr, 6),  # TODO: INCLUDE MORE DIGITS?
                '#training_subject': True,
                '#feedback_1_id': negative_feedback_id})
        return negative_subjects_metadata_dicts

    @staticmethod
    def copy_rename_negative_images(negative_subjects_metadata_dicts):
        """
        Copies negative-qualified experiment images from the 'fetched_images' folder to the 'negative_images' folder,
        renaming the file according to the file name defined in its 'metadata_dict'.
            negative_subjects_metadata_dicts: dictionaries corresponding to negative subjects' metadata rows
        """
        for d in negative_subjects_metadata_dicts:
            experiment_file_path = os.path.join(fetched_images_folder, d['#exp_file_name'])
            negative_file_path = os.path.join(negative_subjects_folder, d['#file_name'])
            copyfile(experiment_file_path, negative_file_path)

    def write_metadata(self, negative_subjects_metadata_dicts):
        """
        Writes negatives subjects' metadata  into 'negative_subjects.csv', 'Negative_Manifest.xlsx,
        and 'Negative_Manifest.csv' (the backup manifest).
            negative_subjects_metadata_dicts: dictionaries corresponding to negative subjects' metadata rows
        """
        self.negative_csv.write_rows(negative_subjects_metadata_dicts, dict_writer=True)
        self.negative_manifest.write_rows(negative_subjects_metadata_dicts, dict_writer=True)
        self.negative_manifest_csv.write_rows(negative_subjects_metadata_dicts, dict_writer=True)

    def upload(self):
        """
        Uploads negative images to Zooniverse and Google Drive, and manifests to Google Drive and Github
        """
        upload_subjects_to_zooniverse(negative_csv_path, negative_subject_set_id)
        self.gd.upload_folder(negative_subjects_folder, negative_folder_drive_id)
        # push_files_to_GitHub(negative_manifest_path, negative_manifest_csv_path)  # TODO: UNCOMMENT
        self.gd.upload_file(negative_manifest_path, manifests_folder_drive_id, replace_existing=True)
        self.gd.upload_file(negative_manifest_csv_path, manifests_csv_folder_drive_id, replace_existing=True)
