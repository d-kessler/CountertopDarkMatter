import os

from python.classification_analysis.process_classifications_csv import ProcessClassificationsCSV
from python.classification_analysis.run_swap import SWAP
from python.classification_analysis.create_negatives import CreateNegatives
from python.classification_analysis.promote_subjects import PromoteSubjects
from python.classification_analysis.consensus_analysis import ConsensusAnalysis

from python.utils.file_utils import remove_file
from python.utils.git_utils import push_files_to_GitHub
from python.google_drive_folder.google_drive import GoogleDriveUtils

from python.vars.project_info import first_workflow_id
from python.vars.thresholds import retirement_lower_threshold, promotion_threshold, \
    first_workflow_classification_limit
from python.vars.paths_and_ids import offline_swap_db_path, \
    swap_classifications_csv_path, golds_csv_path, \
    swap_classifications_manifest_path, golds_manifest_path, \
    swap_classifications_manifest_csv_path, golds_manifest_csv_path, \
    consensus_classifications_csv_path, \
    consensus_classifications_manifest_path, consensus_classifications_manifest_csv_path, \
    consensus_subjects_manifest_csv_path, consensus_users_manifest_csv_path, \
    consensus_subjects_manifest_path, consensus_users_manifest_path, \
    cleaned_classifications_manifest_path, cleaned_classifications_manifest_csv_path, \
    databases_folder_drive_id, manifests_csv_folder_drive_id, manifests_folder_drive_id

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir("..")


"""
    Performs the following:
        I. `process_classification_export':
            1. Downloads updated Zooniverse classification export
            2. Writes the following converted-classification CSVs:
                a. `unprocessed_classifications'
                    - Classifications not yet processed
                b. `cleaned_classifications'
                    - Flattens embedded lists and dicts
                    - Ignores unnecessary fields
                    - Adds some custom fields
                c. `swap_classifications'
                    - annotations['value'] field is converted to SWAP (0 or 1) format
                d. `gold_classifications'
                    - Identifies training subjects by type
                        0 = Negative
                        1 = Positive (simulation)
                    - Formats two columns as follows:
                      'Zooniverse subject ID': gold label (0 or 1)
            3. Writes (appends) to running manifests corresponding to the above CSVs
        II. `run_kSWAP'
            1. 2-class kSWAP is ran on `swap_classifications' and  `gold_classifications'
               with the following effects:
                a. `offline_swap.db' is updated with user scores and subject probabilities
                b. Subjects whose null (0) probabilities pass the lower threshold are retired on Zooniverse
                c. `swap' and  `swap_config' instances are returned for further analysis
        III. `CreateNegatives'
    """


def main():

    pcc = ProcessClassificationsCSV()
    pcc.process_classification_export(
        download_export=True,
        generate_new_export=True,
        update_first_unprocessed_row=True)

    # remove_file(offline_swap_db_path)
    swap, swap_config = SWAP(
        classifications_csv_path=swap_classifications_csv_path,
        golds_csv_path=golds_csv_path,
        workflow_id=first_workflow_id,
        retirement_lower_threshold=retirement_lower_threshold,
        retirement_classification_limit=first_workflow_classification_limit)

    cn = CreateNegatives(swap=swap)
    cn.run()

    ps = PromoteSubjects(
        swap=swap,
        positive_prior=swap_config.p0['1'],
        promotion_threshold=promotion_threshold,
        clear_folders=True)
    ps.run()

    # TODO: Add retirement after 15 (?) classifications
    ca = ConsensusAnalysis(
        cl_csv_path=consensus_classifications_csv_path,
        subjects_csv_path=consensus_subjects_manifest_csv_path,
        users_csv_path=consensus_users_manifest_csv_path,
        subjects_manifest_path=consensus_subjects_manifest_path,
        users_manifest_path=consensus_users_manifest_path)
    ca.run()

    upload()


def upload():
    # GOOGLE DRIVE
    gd = GoogleDriveUtils()
    # CLEANED CLASSIFICATIONS
    gd.upload_file(cleaned_classifications_manifest_path, manifests_folder_drive_id)
    gd.upload_file(cleaned_classifications_manifest_csv_path, manifests_csv_folder_drive_id)
    # SWAP
    gd.upload_file(offline_swap_db_path, databases_folder_drive_id)
    gd.upload_file(swap_classifications_manifest_path, manifests_folder_drive_id)
    gd.upload_file(golds_manifest_path, manifests_folder_drive_id)
    gd.upload_file(swap_classifications_manifest_csv_path, manifests_csv_folder_drive_id)
    gd.upload_file(golds_manifest_csv_path, manifests_csv_folder_drive_id)
    # CONSENSUS
    gd.upload_file(consensus_classifications_manifest_path, manifests_folder_drive_id)
    gd.upload_file(consensus_subjects_manifest_path, manifests_folder_drive_id)
    gd.upload_file(consensus_users_manifest_path, manifests_folder_drive_id)
    gd.upload_file(consensus_classifications_manifest_csv_path, manifests_csv_folder_drive_id)
    gd.upload_file(consensus_subjects_manifest_csv_path, manifests_csv_folder_drive_id)
    gd.upload_file(consensus_users_manifest_csv_path, manifests_csv_folder_drive_id)
    # GITHUB
    push_files_to_GitHub([cleaned_classifications_manifest_path, cleaned_classifications_manifest_csv_path,
                          offline_swap_db_path, swap_classifications_manifest_path, golds_manifest_path,
                          swap_classifications_manifest_csv_path, golds_manifest_csv_path,
                          consensus_classifications_manifest_path, consensus_subjects_manifest_path,
                          consensus_users_manifest_path, consensus_classifications_manifest_csv_path,
                          consensus_subjects_manifest_csv_path, consensus_users_manifest_csv_path])


if __name__ == "__main__":
    main()
