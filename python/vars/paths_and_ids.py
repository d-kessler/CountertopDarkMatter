import os

# `DATA' FOLDER
unprocessed_images_zeroth_folder = os.path.join("data", "images")
fetched_images_folder = os.path.join("data", "fetched_images")
classifications_csv_path = os.path.join("data", "classifications.csv")

# `PROCESSED_DATA' FOLDER
# -> IMAGES AND CSVs
experiment_subjects_folder = os.path.join("processed_data", "experiment_subjects")
experiment_csv_path = os.path.join(experiment_subjects_folder, "experiment_subjects.csv")
simulation_subjects_folder = os.path.join("processed_data", "simulation_subjects")
simulation_csv_path = os.path.join(simulation_subjects_folder, "simulation_subjects.csv")
negative_subjects_folder = os.path.join("processed_data", "negative_subjects")
negative_csv_path = os.path.join(negative_subjects_folder, "negative_subjects.csv")
marking_subjects_folder = os.path.join("processed_data", "marking_subjects")
marking_csv_path = os.path.join(marking_subjects_folder, "marking_subjects.csv")
# -> CONVERTED_CLASSIFICATIONS
converted_classifications_folder = os.path.join("processed_data", "converted_classifications")
unprocessed_classifications_csv_path = os.path.join(converted_classifications_folder, "unprocessed_classifications.csv")
cleaned_classifications_csv_path = os.path.join(converted_classifications_folder, "cleaned_classifications.csv")
swap_classifications_csv_path = os.path.join(converted_classifications_folder, "swap_classifications.csv")
golds_csv_path = os.path.join(converted_classifications_folder, "golds.csv")
consensus_classifications_csv_path = os.path.join(converted_classifications_folder, "consensus_classifications.csv")

# `RECORDS' FOLDER
records_folder = "records"
# -> CLASSIFICATION_ANALYSIS
classification_analysis_records = os.path.join(records_folder, "classification_analysis")
offline_swap_db_path = os.path.join(classification_analysis_records, "offline_swap.db")
consensus_subjects_manifest_path = os.path.join(classification_analysis_records, "Consensus_Subjects.xlsx")
consensus_users_manifest_path = os.path.join(classification_analysis_records, "Consensus_Users.xlsx")
# -> -> CSV
classification_analysis_records_csv = os.path.join(classification_analysis_records, "csv")
consensus_subjects_manifest_csv_path = os.path.join(classification_analysis_records_csv, "consensus_subjects.csv")
consensus_users_manifest_csv_path = os.path.join(classification_analysis_records_csv, "consensus_users.csv")
# -> CLASSIFICATIONS
classification_records = os.path.join(records_folder, "classifications")
cleaned_classifications_manifest_path = os.path.join(classification_records, "Cleaned_Classifications.xlsx")
swap_classifications_manifest_path = os.path.join(classification_records, "Swap_Classifications.xlsx")
golds_manifest_path = os.path.join(classification_records, "Golds.xlsx")
consensus_classifications_manifest_path = os.path.join(classification_records, "Consensus_Classifications.xlsx")
# -> -> CSV
classification_records_csv = os.path.join(classification_records, "csv")
cleaned_classifications_manifest_csv_path = os.path.join(classification_records_csv, "cleaned_classifications.csv")
swap_classifications_manifest_csv_path = os.path.join(classification_records_csv, "swap_classifications.csv")
golds_manifest_csv_path = os.path.join(classification_records_csv, "golds.csv")
consensus_classifications_manifest_csv_path = os.path.join(classification_records_csv, "consensus_classifications.csv")
# -> PROCESSING
processing_records = os.path.join(records_folder, "processing")
name_id_manifest_path = os.path.join(processing_records, "Name_ID.xlsx")
first_unprocessed_row_manifest_path = os.path.join(processing_records, "First_Unprocessed_Row.xlsx")
processed_folders_manifest_path = os.path.join(processing_records, "Processed_Folders.xlsx")
processed_slabs_manifest_path = os.path.join(processing_records, "Processed_Slabs.xlsx")
# -> -> CSV
processing_records_csv = os.path.join(processing_records, "csv")
name_id_manifest_csv_path = os.path.join(processing_records_csv, "nameID_manifest.csv")
first_unprocessed_row_manifest_csv_path = os.path.join(processing_records_csv, "first_unprocessed_row.csv")
processed_folders_manifest_csv_path = os.path.join(processing_records_csv, "processed_folders.csv")
processed_slabs_manifest_csv_path = os.path.join(processing_records_csv, "processed_slabs.csv")
# -> SUBJECTS
subject_records = os.path.join(records_folder, "subjects")
experiment_manifest_path = os.path.join(subject_records, "Experiment_Manifest.xlsx")
simulation_manifest_path = os.path.join(subject_records, "Simulation_Manifest.xlsx")
negative_manifest_path = os.path.join(subject_records, "Negative_Manifest.xlsx")
marking_manifest_path = os.path.join(subject_records, "Marking_Manifest.xlsx")
# -> -> CSV
subject_records_csv = os.path.join(subject_records, "csv")
experiment_manifest_csv_path = os.path.join(subject_records_csv, "experiment_manifest.csv")
simulation_manifest_csv_path = os.path.join(subject_records_csv, "simulation_manifest.csv")
negative_manifest_csv_path = os.path.join(subject_records_csv, "negative_manifest.csv")
marking_manifest_csv_path = os.path.join(subject_records_csv, "marking_manifest.csv")

# GOOGLE DRIVE FOLDER IDs
experiment_folder_drive_id = "1JZQLCdTKSkEZJlIQY7G4wc73CiQ0gKFw"
simulation_folder_drive_id = "1zRQgOLWDLknWMHpGuMvA5-N-aOZ1XCER"
negative_folder_drive_id = "1G3lCglDdZrpRp_NWDY0910lFdmiLO2pJ"
marking_folder_drive_id = "1sit01wve1VT3cFarVVKlwn1yLabeuoXD"
repository_folder_drive_id = "17KBIis4L7uNnqyfRfKm0Wl9FmftdF_lF"
records_folder_drive_id = "1bDnbLE5T9CmmwpuCc2nNUSswa_x60AEk"
manifests_folder_drive_id = "1kwbhMxC1X8U2XvJnAHhtGUnO9jgJ7c50"
manifests_csv_folder_drive_id = "1wqcFRf2r4OkTenGoEC7AUYolpPLXje1G"
databases_folder_drive_id = "1GtB5zam3EysLHKq7KFZqbzu8jP_opRhu"
uploaded_folder_drive_id = "1_dvHbUf0JyK_PioAAvw4gEf7dXtz15HW"
staging_ground_folder_drive_id = "1QkugwBaBzCzjBjn2czx4U6-tME6DfV7K"
