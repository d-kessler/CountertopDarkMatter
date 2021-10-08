# CLASSIFICATION ANALYSIS

consensus_subjects_fieldnames = ['subject_id', 'score', 'user_weight_sum', 'n_users',
                                 'classifications', 'score_history']
consensus_users_fieldnames = ['user_id', 'weight', 'n_subjects', 'classifications', 'weight_history']

# CLASSIFICATIONS
# Note: the SWAP classifications manifest's fieldnames are the same as the ones in the Zooniverse-generated
# 'classifications.csv'. The cleaned classifications manifests' fieldnames are the combined fieldnames of all
# subject types, along with some of the fieldnames in 'classifications.csv', and some custom fieldnames
golds_fieldnames = ["subject_id", "gold"]
consensus_classification_fieldnames = ['classification_id', 'subject_id', 'user_id', 'label']

# SUBJECTS
experiment_fieldnames = ['!subject_id', '#file_name', '#second_folder', "#first_folder",
                         '#pre_file_name', '#resize_factor', '#warehouse', '#location',
                         '#granite_type', '#slab_id', '#date', '#lat_long', '#columns_or_rows',
                         '#image_dimensions(in)', '#glare_area(mm^2)', '#countable_area(mm^2)',
                         '#grain_density', '#grain_stats(mm)', '#scale_bar_parameters(mm)']
simulation_fieldnames = ['!subject_id', '#file_name', '#training_subject', '#feedback_1_id',
                         '#feedback_1_x', '#feedback_1_y', '#feedback_1_toleranceA',
                         '#feedback_1_toleranceB', '#feedback_1_theta', '#major_to_minor_ratio',
                         '#appearance_parameters']
negative_fieldnames = ['!subject_id', '#file_name', '#exp_file_name', '#cumulative_fnr',
                       '#training_subject', '#feedback_1_id']
marking_fieldnames = ["!subject_id", "#subject_znv_id", "#file_name", "#exp_file_name", "#second_folder_name",
                      "#first_folder_name", "#pre_file_name", "#warehouse", "#location",
                      "#latitude_longitude", "#slab_id", "#columns_or_rows", "#image_dimensions(in)",
                      "#resize_factor", "#average_cx", "#average_cy", "#average_xdim", "#average_ydim",
                      "#average_angle", "#number_of_classifications", "#positive_probability",
                      "#classification_ids", "#subject_history", "#appearance_parameters"]

# PROCESSING
first_unprocessed_row_fieldnames = ["date", "rows_processed", "first_unprocessed_row"]
name_id_fieldnames = ['file_name', 'google_drive_id']
processed_folders_fieldnames = ['date_processed', 'first_folder', 'second_folders',
                                'experiment_id_endpoints', 'simulation_id_endpoints']
processed_slabs_fieldnames = ['number', 'slab_id', 'granite_type', 'warehouse', 'location', 'columns_or_rows',
                              'number_columns_or_rows', 'date_imaged', 'images_taken', 'image_dimensions']
