import os
import sys
from pathlib import Path
from panoptes_client import \
    Panoptes, Project, SubjectSet, Workflow
from panoptes_client import Subject as PanoptesSubject
    
from python.vars.paths_and_ids import classifications_csv_path
from python.vars.zooniverse_login import zooniverse_username, zooniverse_password
from python.vars.project_info import project_id, \
    simulation_subject_set_id, negative_subject_set_id, \
    first_workflow_id, second_workflow_id, \
    training_chances, training_chances_default

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir(os.path.join(".."))


"""
NOTE: Before attempting to upload images to Zooniverse from a new computer, enter into the command line
                                    "panoptes configure" ,
then enter a collaborator's Zooniverse username and password (the password text will be hidden).
"""


def upload_subjects_to_zooniverse(csv_file_path, subject_set_id, file_names_column=None):
    """
    Uploads subjects (images) to Zooniverse.py given the requisite CSV.
        csv_file_path = path to the csv file containing subjects' file names and metadata
        subject_set_id = ID of the Zooniverse subject set to upload to
        file_names_column = column number of the CSV in which subjects' files names are given
    """
    if file_names_column:
        upload_cmd = f"panoptes subject-set upload-subjects -f {file_names_column} -M {subject_set_id} {csv_file_path}"
    else:
        upload_cmd = f"panoptes subject-set upload-subjects -M {subject_set_id} {csv_file_path}"
    try:
        os.system(upload_cmd)
    except:
        print(f'Error uploading {csv_file_path} subjects; upload manually.')


class ZooniverseUtils:
    def __init__(self, workflow_id='first'):
        self.username = zooniverse_username
        self.password = zooniverse_password
        if workflow_id == 'first':
            workflow_id = first_workflow_id
        elif workflow_id == 'second':
            workflow_id = second_workflow_id
        self.workflow_id = workflow_id
        self.panoptes_project, self.panoptes_workflow = self.configure_zooniverse()

    def configure_zooniverse(self):
        """
        Connects to Zooniverse, returns Panoptes (Zooniverse API) project and workflow class instances.
        """
        # Connect to Zooniverse, get project & workflow ID's
        Panoptes.connect(username=self.username, password=self.password)
        panoptes_project = Project.find(project_id)
        panoptes_project.save()
        panoptes_workflow = Workflow.find(self.workflow_id)
        panoptes_workflow.save()
        return panoptes_project, panoptes_workflow
    
    @staticmethod
    def get_panoptes_subject(zooniverse_subject_id):
        """
        Returns the PanoptesSubject instance of a subject given its Zooniverse ID (integer).
        """
        return PanoptesSubject().find(zooniverse_subject_id)
    
    def retire_subjects(self, zooniverse_subject_ids):
        """
        Retires subjects on Zooniverse given their Zooniverse subject IDs.
            zooniverse_subject_ids = list of Zooniverse subject IDs (ints)
        """
        panoptes_subjects = []
        for zooniverse_subject_id in zooniverse_subject_ids:
            panoptes_subject = self.get_panoptes_subject(zooniverse_subject_id)
            panoptes_subjects.append(panoptes_subject)
        self.panoptes_workflow.retire_subjects(panoptes_subjects)

    def configure_designator(self):
        """
        Configures "Designator", which determines frequency with which training images are shown to users.
        """
        self.panoptes_workflow.configuration['training_set_ids'] = [simulation_subject_set_id, negative_subject_set_id]
        self.panoptes_workflow.configuration['training_chances'] = training_chances
        self.panoptes_workflow.configuration['training_default_chances'] = training_chances_default
        self.panoptes_workflow.configuration[
            'subject_queue_page_size'] = 10  # how many subjects are loaded in queue at one time
        # Training subjects are not retired, experiment subjects are retired via SWAP
        self.panoptes_workflow.retirement['criteria'] = 'never_retire'
        self.panoptes_workflow.modified_attributes.add('configuration')
        self.panoptes_workflow.save()

    def generate_classification_export(self, destination_path=None, generate_new=False):
        """
        Generates a Zooniverse classification export.
            destination_path: path to which the export CSV is saved
            generate_new: boolean for whether a new export (with the latest classifications) should be requested
                NOTE: new exports can only be request once every 12 hours
        """
        if destination_path is None:
            destination_path = classifications_csv_path
        Panoptes.connect(username=self.username, password=self.password)
        classification_export = self.panoptes_project.get_export('classifications', generate=generate_new)
        export_file = Path(destination_path)
        export_file.write_bytes(classification_export.content)

    def create_subject_set(self, subject_set_name):
        """
        Creates a Zooniverse subject set with the given name.
        """
        subject_set = SubjectSet()
        subject_set.links.project = self.panoptes_project
        subject_set.display_name = subject_set_name
        subject_set.save()
        self.panoptes_workflow.links.subject_sets.add(subject_set)
        self.panoptes_workflow.save()
        self.configure_designator()
