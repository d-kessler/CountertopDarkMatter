import os

from python.classification_analysis.kswap import kSWAP
from python.classification_analysis.offline_swap_config import Config

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir("..")


def SWAP(classifications_csv_path, golds_csv_path, workflow_id, retirement_lower_threshold,
         retirement_classification_limit):
    # Retrieve swap configuration from 'offline_swap_config.py'
    swap_config = Config(workflow_id, retirement_lower_threshold, retirement_classification_limit)
    # Create a kSWAP instance
    swap = kSWAP(config=swap_config)
    # Load subjects, users from 'offline_swap.db'
    swap = swap.load()
    # Run kSWAP on CSV files
    swap.run_offline(golds_csv_path, classifications_csv_path)
    # Save new subjects, users to 'offline_swap.db'
    swap.save()
    # Retrieve updated 'subjects', 'users' dictionaries from 'offline_swap.db'
    del swap
    swap = kSWAP(config=swap_config)
    swap = swap.load()
    return swap, swap_config
