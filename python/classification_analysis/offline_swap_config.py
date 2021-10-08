import os

from python.vars.project_info import project_id
from python.vars.paths_and_ids import converted_classifications_folder, \
    classification_analysis_records, offline_swap_db_path

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir("..")


class Config(object):
    def __init__(self, workflow_id, retirement_lower_threshold, retirment_classification_limit):
        self.project = project_id
        self.workflow = workflow_id
        self.swap_path = '.' + os.path.sep
        self.data_path = converted_classifications_folder + os.path.sep
        self.db_name = os.path.basename(offline_swap_db_path)
        self.db_path = classification_analysis_records + os.path.sep

        self.label_map    = {'0': 0, '1': 1}
        self.user_default = {'0': [0.50, 0.50], '1': [0.50, 0.50]}
        self.p0           = {'0': 0.9, '1': 0.01}
        # below, the first entry is WRT the ratio of posterior to prior tenebrite probability; the second entry is unused
        self.thresholds   = (retirement_lower_threshold, 1)
        self.retirement_limit = retirment_classification_limit
        self.gamma = 1
