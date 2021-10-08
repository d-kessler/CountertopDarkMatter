import os
import re
import json
from datetime import date, datetime

from python.utils.zooniverse_utils import ZooniverseUtils
from python.utils.csv_excel_utils import CsvUtils, ExcelUtils, fill_dict_from_dict
from python.vars.project_info import first_workflow_id, beta_group_2_first_workflow_id, second_workflow_id
from python.vars.paths_and_ids import experiment_manifest_path, simulation_manifest_path, negative_manifest_path, \
    marking_manifest_path, classifications_csv_path, unprocessed_classifications_csv_path, \
    cleaned_classifications_csv_path, swap_classifications_csv_path, golds_csv_path, \
    cleaned_classifications_manifest_path, swap_classifications_manifest_path, golds_manifest_path, \
    first_unprocessed_row_manifest_path, cleaned_classifications_manifest_csv_path, \
    swap_classifications_manifest_csv_path, golds_manifest_csv_path, \
    first_unprocessed_row_manifest_csv_path, consensus_classifications_csv_path, \
    consensus_classifications_manifest_path, consensus_classifications_manifest_csv_path
from python.vars.fieldnames import consensus_classification_fieldnames, golds_fieldnames, \
    first_unprocessed_row_fieldnames

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir(os.path.join(".."))


class ProcessClassificationsCSV:
    first_valid_row = 100  # TODO: UPDATE FIRST_UNPROCESSED MANIFEST WITH THIS (CORRECTED) VALUE

    def __init__(self):
        """
        Creating 'CsvUtils' and 'ExcelUtils' for all relevant CSV data-files and manifests (excel & CSV record-files).
        """
        # Classifications CSV obtained from Zooniverse
        self.classifications_csv = CsvUtils(classifications_csv_path)
        # CSV of classifications not previously processed
        self.unprocessed_classifications_csv = CsvUtils(unprocessed_classifications_csv_path,
                                                        self.classifications_csv.fieldnames_list)
        # Cleaned (flatted and reformatted, with some custom columns) classifications CSV
        self.cleaned_classifications_fieldnames = self.get_cleaned_classifications_fieldnames()
        self.cleaned_classifications_csv = CsvUtils(cleaned_classifications_csv_path,
                                                    self.cleaned_classifications_fieldnames)
        # Classifications CSV wherein first-workflow annotations are converted into a form amenable to (k)SWAP
        self.swap_classifications_csv = CsvUtils(swap_classifications_csv_path,
                                                 self.classifications_csv.fieldnames_list)
        # CSV used by (k)SWAP; contains the Zooniverse subject IDs and 'gold labels' (actual classifications)
        # of training subjects
        self.golds_csv = CsvUtils(golds_csv_path, golds_fieldnames)
        # CSV used by 'consensus_analysis' for classifications made on the 'Inspect' workflow
        self.consensus_classifications_csv = CsvUtils(consensus_classifications_csv_path,
                                                      consensus_classification_fieldnames)
        # Manifests (excel files) keeping running-records of the data written into the aforementioned CSVs
        self.cleaned_classifications_manifest = ExcelUtils(cleaned_classifications_manifest_path,
                                                           self.cleaned_classifications_fieldnames)
        self.swap_classifications_manifest = ExcelUtils(swap_classifications_manifest_path,
                                                        self.classifications_csv.fieldnames_list)
        self.golds_manifest = ExcelUtils(golds_manifest_path, golds_fieldnames)
        self.consensus_classifications_manifest = ExcelUtils(consensus_classifications_manifest_path,
                                                             consensus_classification_fieldnames)
        # Manifest tracking which rows of classifications have been processed on which dates
        self.first_unprocessed_row_manifest = ExcelUtils(first_unprocessed_row_manifest_path,
                                                         first_unprocessed_row_fieldnames)
        # Manifest backups (CSVs), to protect against seemingly-random corruption
        self.cleaned_classifications_manifest_csv = CsvUtils(cleaned_classifications_manifest_csv_path,
                                                             self.cleaned_classifications_manifest.fieldnames_list)
        self.swap_classifications_manifest_csv = CsvUtils(swap_classifications_manifest_csv_path,
                                                          self.swap_classifications_manifest.fieldnames_list)
        self.golds_manifest_csv = CsvUtils(golds_manifest_csv_path, self.golds_manifest.fieldnames_list)
        self.consensus_classifications_manifest_csv = CsvUtils(consensus_classifications_manifest_csv_path,
                                                               consensus_classification_fieldnames)
        self.first_unprocessed_row_manifest_csv = CsvUtils(first_unprocessed_row_manifest_csv_path,
                                                           self.first_unprocessed_row_manifest.fieldnames_list)

    def process_classification_export(self, download_export=False, generate_new_export=False,
                                      update_first_unprocessed_row=False, start_row=None, end_row=None):
        """
        Performs all the necessary processing for a new Zooniverse classifications export.
            download_export: 'True' if the classifications export need be downloaded, 'False' if it exists locally
            generate_new_export: 'True' if a new export need be generated (to include the most recent classifications);
                                 'False' to use the last generated. Only needed if 'generate' is True.
            update_first_unprocessed_row: 'True' to update the manifest tracking which classifications have been processed
            start_row: Zooniverse classifications CSV row number at which to start processing;
                       overwrites the default 'first_unprocessed_row'
            end_row: Zooniverse classifications CSV row number at which to end processing;
                     if None, process all classifications past 'first_unprocessed_row' (or 'start_row', if given)
        """
        if download_export is True:
            ZooniverseUtils().generate_classification_export(generate_new=generate_new_export)
        rows_processed, new_first_unprocessed_row = self.write_unprocessed_classifications_csv(start_row, end_row)
        if update_first_unprocessed_row is True:
            self.update_first_unprocessed_row_csv(rows_processed, new_first_unprocessed_row)
        self.write_cleaned_classifications()
        first_workflow_unprocessed_rows, second_workflow_unprocessed_rows = self.separate_unprocessed_rows()
        self.write_swap_classifications(first_workflow_unprocessed_rows)
        self.write_consensus_classifications(second_workflow_unprocessed_rows)

    def write_unprocessed_classifications_csv(self, start_row=None, end_row=None):
        """
        Writes a CSV of unprocessed classifications using the rows of the 'classifications.csv'
        Zooniverse export and the information in the 'first_unprocessed_row.xlsx' manifest.
            start_row: Zooniverse classifications CSV row number at which to start processing;
                       overwrites the default 'first_unprocessed_row' obtained from 'first_unprocessed_row.xlsx'
            end_row: Zooniverse classifications CSV row number at which to end processing;
                     if None, process all classifications past 'first_unprocessed_row' (or 'start_row', if given)
        """
        self.unprocessed_classifications_csv.clear()
        if not start_row:
            start_row = self.get_first_unprocessed_row()
        unprocessed_rows = self.classifications_csv.read_rows(start_row=start_row - 1, end_row=end_row)
        self.unprocessed_classifications_csv.write_rows(unprocessed_rows)
        rows_processed = len(unprocessed_rows)
        new_first_unprocessed_row = start_row + rows_processed + 1
        return rows_processed, new_first_unprocessed_row

    def get_first_unprocessed_row(self):
        """
        Retrieves from 'first_unprocessed_row.xlsx' manifest the number of the first row of the
        'classifications.csv' Zooniverse export that has not yet been processed.
        """
        rows = self.first_unprocessed_row_manifest.read_rows(start_row=1)
        if rows == first_unprocessed_row_fieldnames:
            return 0
        return int(rows[-1][-1])

    def update_first_unprocessed_row_csv(self, rows_processed, new_first_unprocessed_row):
        """
        Updates the 'first_unprocessed_row.xlsx' manifest with information about the classifications just processed.
        """
        self.first_unprocessed_row_manifest.write_rows([date.today().strftime("%m-%d-%Y"), rows_processed,
                                                        new_first_unprocessed_row])
        self.first_unprocessed_row_manifest_csv.write_rows([date.today().strftime("%m-%d-%Y"), rows_processed,
                                                            new_first_unprocessed_row])

    def separate_unprocessed_rows(self):
        """
        Separates the unprocessed rows corresponding to classifications coming from the 'first' and 'second' workflows.
        """
        unprocessed_rows = self.unprocessed_classifications_csv.read_rows(dict_reader=True)
        first_workflow_rows, second_workflow_rows = [], []
        for unprocessed_row in unprocessed_rows:
            workflow_id = int(unprocessed_row['workflow_id'])
            if workflow_id in [first_workflow_id, beta_group_2_first_workflow_id]:
                first_workflow_rows.append(unprocessed_row)
            elif workflow_id == second_workflow_id:
                second_workflow_rows.append(unprocessed_row)
        return first_workflow_rows, second_workflow_rows

    def write_cleaned_classifications(self):
        """
        Writes the CSV of 'cleaned' classifications (flattening embedded data structures, ignoring unnecessary
        fields, and adding some custom fields), appends to the running CSV and manifest.
        """
        self.cleaned_classifications_csv.clear()
        clean_row_template = self.get_clean_row_template(self.cleaned_classifications_fieldnames)
        rows = self.parse_rows(self.unprocessed_classifications_csv)
        clean_rows = []
        for row in rows:
            clean_row = clean_row_template.copy()
            metadata = self.flatten_dict(row['metadata'])
            annotations = self.flatten_dict(row['annotations'])
            subject_data = self.flatten_dict(row['subject_data'])
            custom_fields = self.get_custom_fields(metadata, subject_data, annotations)
            for data_dict in [row, metadata, annotations, subject_data, custom_fields]:
                clean_row = fill_dict_from_dict(clean_row, data_dict, convert_types_to_string=[bool])
            clean_rows.append(clean_row)
        self.cleaned_classifications_csv.write_rows(clean_rows, dict_writer=True)
        self.cleaned_classifications_manifest.write_rows(clean_rows, dict_writer=True)
        self.cleaned_classifications_manifest_csv.write_rows(clean_rows, dict_writer=True)

    @staticmethod
    def get_clean_row_template(organized_fieldnames):
        """
        Returns a template dict for a row of the cleaned classifications CSV.
        """
        return dict((fieldname, None) for fieldname in organized_fieldnames)

    def get_cleaned_classifications_fieldnames(self):
        """
        Organizes all fieldnames to appear in the cleaned classifications CSV.
        """
        experiment_fieldnames = (ExcelUtils(experiment_manifest_path)).fieldnames_list
        simulation_fieldnames = (ExcelUtils(simulation_manifest_path)).fieldnames_list
        negative_fieldnames = (ExcelUtils(negative_manifest_path)).fieldnames_list
        marking_fieldnames = (ExcelUtils(marking_manifest_path)).fieldnames_list
        custom_fieldnames = ['user_device', 'seconds_spent_classifying', 'subject_znv_id', '!subject_id',
                             'subject_type', 'classification', 'ellipse_adjusted', 'success']
        zooniverse_fieldnames = ['classification_id', 'workflow_id', 'workflow_name', 'user_name', 'user_id',
                                 'user_ip', 'gold_standard', 'expert', custom_fieldnames[0], 'subject_dimensions',
                                 'created_at', *custom_fieldnames[1:4], 'already_seen', 'retired']
        annotation_fieldnames = ['tool_label', *custom_fieldnames[4:], 'x', 'y', 'rx', 'ry', 'angle']
        organized_fieldnames = self.organize_fieldnames(zooniverse_fieldnames, experiment_fieldnames,
                                                        annotation_fieldnames, simulation_fieldnames,
                                                        negative_fieldnames, marking_fieldnames)
        return organized_fieldnames

    @staticmethod
    def organize_fieldnames(*fieldnames_lists):
        """
        Combines the list of lists 'fieldnames_lists' into a single list without duplicates
        """
        organized_fieldnames = []
        for fieldnames_list in fieldnames_lists:
            [organized_fieldnames.append(fn) for fn in fieldnames_list if fn not in organized_fieldnames]
        return organized_fieldnames

    @staticmethod
    def parse_rows(classifications_csv, start_row=None, end_row=None):
        """
        Using JSON to load the data structures of the classification CSV into python objects.
        """
        rows = classifications_csv.read_rows(start_row, end_row, dict_reader=True)
        for row in rows:
            row['metadata'] = json.loads(row['metadata'])
            row['annotations'] = json.loads(row['annotations'])[0]
            row['subject_data'] = json.loads(row['subject_data'].replace("null", "false"))
        return rows

    @staticmethod
    def flatten_dict(dictionary):
        """
        Appends key-value pairs from dictionaries inside 'dictionary' to 'dictionary'.
        """
        sub_dict_keys = []
        for key in dictionary.keys():
            if type(dictionary[key]) == dict:
                sub_dict_keys.append(key)
            elif type(dictionary[key]) == list:
                sub_dict_keys.append(key)
        for sub_dict_key in sub_dict_keys:
            if type(dictionary[sub_dict_key]) == dict:
                for key in dictionary[sub_dict_key].keys():
                    dictionary[key] = dictionary[sub_dict_key][key]
            elif type(dictionary[sub_dict_key]) == list:
                if not dictionary[sub_dict_key] or dictionary[sub_dict_key] == \
                        [None for i in range(len(dictionary[sub_dict_key]))]:
                    continue
                for sub_dict in dictionary[sub_dict_key]:
                    for key in sub_dict.keys():
                        dictionary[key] = sub_dict[key]
            # dictionary.pop(sub_dict_key)
        return dictionary

    def get_custom_fields(self, metadata, subject_data, annotations):
        """
        Uses information from the 'classifications.csv' Zooniverse export to create new, useful column data.
        """
        custom_fields = {'user_device': metadata['user_agent'].split('(')[1].split(')')[0]}
        y0, m0, d0, h0, mi0, s0, ms0 = [int(s) for s in re.split("[-T:Z.]", metadata['started_at']) if s != '']
        y, m, d, h, mi, s, ms = [int(s) for s in re.split("[-T:Z.]", metadata['finished_at']) if s != '']
        start_time = datetime(year=y0, month=m0, day=d0, hour=h0, minute=mi0, second=s0, microsecond=ms0)
        end_time = datetime(year=y, month=m, day=d, hour=h, minute=mi, second=s, microsecond=ms)
        custom_fields['seconds_spent_classifying'] = (end_time - start_time).total_seconds()
        custom_fields['subject_znv_id'] = list(subject_data.keys())[0]
        if 'e' in subject_data['!subject_id']:
            custom_fields['subject_type'] = "experiment"
        elif 's' in subject_data['!subject_id']:
            custom_fields['subject_type'] = "simulation"
        elif 'n' in subject_data['!subject_id']:
            custom_fields['subject_type'] = "negative"
        elif 'm' in subject_data['!subject_id']:
            custom_fields['subject_type'] = "marking"
        custom_fields['classification'] = self.get_classification_type(annotations)
        try:
            custom_fields['ellipse_adjusted'] = (float(annotations['rx']) / float(annotations['ry']) != 2.0)
        except KeyError:
            pass
        try:
            custom_fields['success'] = list(metadata['feedback'].values())[0][0]['success']
        except KeyError:
            pass
        return custom_fields

    @staticmethod
    def get_classification_type(annotations):
        """
        Gets a description of the classification made using the annotations['value'] of a 'classifications.csv' row.
        """
        value = annotations['value']
        classification_type = None
        if not value:
            classification_type = "Null Ellipse"
        elif value and type(value) == list:
            classification_type = "Ellipse"
        elif type(value) == str:
            classification_type = value  # "Yes" or "No"
        return classification_type

    def write_swap_classifications(self, first_workflow_unprocessed_rows):
        """
        Writes SWAP-converted annotations and 'golds' CSVs.
        """
        self.swap_classifications_csv.clear()
        self.golds_csv.clear()
        swap_classification_rows = []
        gold_rows = []
        for row in first_workflow_unprocessed_rows:
            metadata, annotations, subject_data = \
                json.loads(row['metadata']), json.loads(row['annotations'])[0], json.loads(row['subject_data'])
            if annotations['value']:
                label = 'positive'
            else:
                label = 'negative'
            subject_type = list(subject_data.values())[0]['!subject_id'][0]
            try:
                success = list(metadata['feedback'].values())[0][0]['success']
            except KeyError:
                success = None  # (applies to experiment images)
            annotations['value'] = self.get_swap_annotation_value(subject_type, label, success)
            annotations.pop("task_label", None)
            row['annotations'] = json.dumps([annotations])
            swap_classification_rows.append(row)
            gold_label = None
            if subject_type == "e":
                continue
            elif subject_type == "s":
                gold_label = 1
            elif subject_type == "n":
                gold_label = 0
            subject_znv_id = list(subject_data.keys())[0]
            gold_row = {'subject_id': subject_znv_id, 'gold': str(gold_label)}
            gold_rows.append(gold_row)
        self.swap_classifications_csv.write_rows(swap_classification_rows, dict_writer=True)
        self.swap_classifications_manifest.write_rows(swap_classification_rows, dict_writer=True)
        self.swap_classifications_manifest_csv.write_rows(swap_classification_rows, dict_writer=True)
        if gold_rows:
            self.golds_csv.write_rows(gold_rows, dict_writer=True)
            self.golds_manifest.write_rows(gold_rows, dict_writer=True)
            self.golds_manifest_csv.write_rows(gold_rows, dict_writer=True)

    @staticmethod
    def get_swap_annotation_value(subject_type, label=None, success=None):
        """
        Returns (k)SWAP-able annotation value.
            subject_type: 'e' for experiment, 's' for simulation, and 'n' for negative
            label: 'positive' or 'negative', depending on whether an annotation was made
                - Only required if the subject is 'experiment' or 'negative'
            success: obtained from Zooniverse; tells whether a training subject was classified correctly
                - Only required if the subject is 'simulation'
                - Note: this parameter is required, as it distinguish true and false positives;
                        a label of 'positive' does not guarantee that the user marked
                        the correct feature
        """
        swap_annotation_value = None
        if (subject_type == "e") or (subject_type == "n"):
            if label == "positive":
                swap_annotation_value = 1
            elif label == "negative":
                swap_annotation_value = 0
        elif subject_type == "s":
            if success is True:
                swap_annotation_value = 1
            elif success is False:
                swap_annotation_value = 0
        return swap_annotation_value

    def write_consensus_classifications(self, second_workflow_unprocessed_rows):
        """
        Writes a CSV amenable to 'consensus_analysis'.
        """
        self.consensus_classifications_csv.clear()
        consensus_classification_rows = []
        for row in second_workflow_unprocessed_rows:
            value = json.loads(row['annotations'])[0]['value']
            label = None
            if value == 'Yes':
                label = 'tenebrite'
            elif value == 'No':
                label = 'negative'
            # For non-logged in users, using 'user_ip' in place of 'user_id'
            user_id = y if (y := row['user_id']) else row['user_ip']
            consensus_classification_rows.append({
                'classification_id': row['classification_id'],
                'subject_id': row['subject_ids'],
                'user_id': user_id,
                'label': label})
        self.consensus_classifications_csv.write_rows(consensus_classification_rows, dict_writer=True)
        self.consensus_classifications_manifest.write_rows(consensus_classification_rows, dict_writer=True)
        self.consensus_classifications_manifest_csv.write_rows(consensus_classification_rows, dict_writer=True)


if __name__ == '__main__':
    pcc = ProcessClassificationsCSV()
    pcc.process_classification_export(download_export=False, update_first_unprocessed_row=False,
                                      start_row=pcc.first_valid_row, end_row=None)
