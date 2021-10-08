project_id = 11726
first_workflow_id = 14437
beta_group_2_first_workflow_id = 16311
second_workflow_id = 18562
experiment_subject_set_id = 95868
simulation_subject_set_id = 95869
negative_subject_set_id = 95870
marking_subject_set_id = 95871

# IDs (names) of the 'feedback rules' in the first workflow
simulation_feedback_id = "meltpatch"
negative_feedback_id = "no_meltpatch"

# Training probabilities in the form:
# [probability] * number of images for which probability is applied
training_chances = [0.5] * 4 + [0.4] * 50 + [0.2] * 50
# Training probability after all the above have been applied
training_chances_default = [0.10]
