import os
import sys
import csv
import json

from python.utils.csv_excel_utils import CsvUtils, ExcelUtils
from python.vars.paths_and_ids import consensus_classifications_csv_path, \
    consensus_subjects_manifest_path, consensus_subjects_manifest_csv_path, \
    consensus_users_manifest_path, consensus_users_manifest_csv_path
from python.vars.fieldnames import consensus_classification_fieldnames, \
    consensus_subjects_fieldnames, consensus_users_fieldnames

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir("..")


"""
Note: 'classification' is in sometimes abbreviated as 'cl'.
"""


class User:
    def __init__(self, user_id, weight=None, n_subjects=None, classifications=None, weight_history=None):
        """
        user_id = user's unique Zooniverse identification number (int)
        weight = the user's weight (int/float)
        n_subjects = the number of subjects that the user has classified (int)
        classifications = list of dictionaries with keys: 'classification_id', 'subject_id', 'user_id', 'label'
        weight_history = list of dictionaries, tracking the progression of user's attributes, with keys:
                         'weight', 'n_subjects', 'subject_id', 'score', 'user_weight_sum', 'n_users'
        """
        self.user_id = user_id
        self.weight = y if (y := weight) else 1  # initial user weight
        self.n_subjects = y if (y := n_subjects) else 0
        self.classifications = y if (y := classifications) else []
        self.weight_history = y if (y := weight_history) else []

    def update_weight(self, subject, label):
        """
        Updates the user's weight with the score of the subject they classified corresponding to the label they submitted.
            subject = Subject object corresponding to the subject the user classified
            label = the label that the user submitted
        """
        # Updating the user's weight
        self.weight = ((self.weight * self.n_subjects) + subject.score[label]) / self.n_subjects
        # Appending the current user and subject attributes to the user's 'weight_history'
        self.weight_history.append(
            {'weight': self.weight, 'n_subjects': self.n_subjects, 'subject_id': subject.subject_id,
             'score': subject.score, 'user_weight_sum': subject.user_weight_sum, 'n_users': subject.n_users})

    def dump(self):
        """
        Returns the user's attributes in list format, with dtypes that can be written to CSVs/manifests.
        """
        return [self.user_id,
                self.weight,
                self.n_subjects,
                json.dumps(self.classifications),
                json.dumps(self.weight_history)]


class Subject:
    def __init__(self, subject_id, score=None, user_weight_sum=None, n_users=None, classifications=None, score_history=None):
        """
        subject_id = subject's unique Zooniverse identification number (int)
        score = the subject's score (float)
        user_weight_sum = the sum of the weights of the users who classified this subject (float)
        n_users = the number of users who classified this subject (int)
        classifications = list of dictionaries with keys: 'classification_id', 'subject_id', 'user_id', 'label'
        score_history = list of dictionaries, tracking the progression of subject's attributes, with keys:
                        'score', 'user_weight_sum', 'n_users', 'user_id', 'weight', 'n_subjects'
        """
        self.subject_id = subject_id
        self.score = y if (y := score) else {'negative': 0, 'tenebrite': 0}
        self.user_weight_sum = y if (y := user_weight_sum) else 0
        self.n_users = y if (y := n_users) else {'negative': 0, 'tenebrite': 0}
        self.classifications = y if (y := classifications) else []
        self.score_history = y if (y := score_history) else []

    def update_score(self, user, label):
        """
        Updates the subject's score corresponding with the label submitted with the user's weight.
            user = User object corresponding to the user that classified the subject
            label = the label that the user submitted
        """
        # Updating the subject's relevant label score
        new_user_weight_sum = self.user_weight_sum + user.weight
        self.score[label] = \
            ((self.score[label] * self.user_weight_sum) + user.weight) / new_user_weight_sum
        self.user_weight_sum = new_user_weight_sum
        # Appending the current subject and user attributes to the subjects's 'score_history'
        self.score_history.append(
            {'score': self.score, 'user_weight_sum': self.user_weight_sum, 'n_users': self.n_users,
             'user_id': user.user_id, 'weight': user.weight, 'n_subjects': user.n_subjects})

    def dump(self):
        """
        Returns the subject's attributes in list format, with dtypes that can be written to CSVs/manifests.
        """
        return [self.subject_id,
                json.dumps(self.score),
                self.user_weight_sum,
                json.dumps(self.n_users),
                json.dumps(self.classifications),
                json.dumps(self.score_history)]


class ConsensusAnalysis:
    cl_fieldnames = consensus_classification_fieldnames
    subject_fieldnames = consensus_subjects_fieldnames
    user_fieldnames = consensus_users_fieldnames

    def __init__(self, cl_csv_path, subjects_csv_path, users_csv_path, subjects_manifest_path, users_manifest_path):
        """
        cl_csv_path = path to the CSV containing classifications with fieldnames 'cl_fieldnames'
        subjects_csv_path = path to the CSV containing subjects' data (fieldnames: 'subject_fieldnames')
        users_csv_path = path to the CSV containing subjects' data (fieldnames: 'subject_fieldnames')
        subjects_manifest_path = path to .xlsx copy of subjects_csv
        users_manifest_path = path to .xlsx copy of users_csv
        """
        # Dictionary with key-value pairs, '(subject ID)': Subject instance
        self.subjects = {}
        # Dictionary with key-value pairs, '(user ID)': User instance
        self.users = {}
        # Class instances used to interface with CSV / manifest (Excel) files
        self.cl_csv = CsvUtils(cl_csv_path, fieldnames_list=self.cl_fieldnames)
        self.subject_csv = CsvUtils(subjects_csv_path, fieldnames_list=self.subject_fieldnames)
        self.user_csv = CsvUtils(users_csv_path, fieldnames_list=self.user_fieldnames)
        self.subject_manifest = ExcelUtils(subjects_manifest_path, fieldnames_list=self.subject_fieldnames)
        self.user_manifest = ExcelUtils(users_manifest_path, fieldnames_list=self.user_fieldnames)

    def run(self, n_iterations=1):
        """
        Performs n_iterations of consensus analysis.
        """
        # Loading previous subject and user data
        self.load_subjects()
        self.load_users()
        # Parsing new classifications, initializing new subjects and users
        self.parse_classifications()
        # Clearing the previous CSVs / manifests
        self.subject_csv.clear()
        self.user_csv.clear()
        self.subject_manifest.clear()
        self.user_manifest.clear()
        # Performing n_iterations of consensus analysis
        self.consensus_analysis(n_iterations)
        # Rewriting CSVs / manifests
        self.update_CSVs()

    def load_subjects(self):
        """
        Loads previous subject data from 'subjects_csv'.
        """
        # Getting a list of all the rows in 'subjects_csv' in dictionary format
        subject_rows = self.subject_csv.read_rows(dict_reader=True)
        for subject_row in subject_rows:
            # Parsing the row, converting to proper data types
            subject_id = int(subject_row['subject_id'])
            score = json.loads(subject_row['score'])
            user_weight_sum = int(subject_row['user_weight_sum'])
            n_users = json.loads(subject_row['n_users'])
            classifications = json.loads(subject_row['classifications'])
            score_history = json.loads(subject_row['score_history'])
            # Adding a Subject instance whose attributes are this row's data to the 'subjects' dictionary
            self.subjects[subject_id] = Subject(
                subject_id, score, user_weight_sum, n_users, classifications, score_history)

    def load_users(self):
        """
        Loads previous user data from 'user_csv'.
        """
        # Getting a list of all the rows in 'users_csv' in dictionary format
        users_rows = self.user_csv.read_rows(dict_reader=True)
        for users_row in users_rows:
            # Parsing the row, converting to proper data types
            user_id = int(users_row['user_id'])
            weight = float(users_row['weight'])
            n_subjects = int(users_row['n_subjects'])
            classifications = json.loads(users_row['classifications'])
            weight_history = json.loads(users_row['weight_history'])
            # Adding a User instance whose attributes are this row's data to the 'users' dictionary
            self.users[user_id] = User(user_id, weight, n_subjects, classifications, weight_history)

    def parse_classifications(self):
        """
        Parses new classifications, initializing new subjects and users.
        """
        # Getting a list of all the rows in 'cl_csv' in dictionary format
        cl_rows = self.cl_csv.read_rows(dict_reader=True)
        for cl_row in cl_rows:
            # Parsing the row, converting to proper data types
            subject_id = cl_row['subject_id'] = int(cl_row['subject_id'])
            user_id = cl_row['user_id'] = int(cl_row['user_id'])
            label = cl_row['label']
            # If the subject is not found 'subjects', add it
            if (y := subject_id) not in self.subjects.keys():
                self.subjects[y] = Subject(y)
            # If the user is not found 'subjects', add it
            if (y := user_id) not in self.users.keys():
                self.users[y] = User(y)
            # Incrementing subject's number of users who classified it
            self.subjects[subject_id].n_users[label] += 1
            # Incrementing the user's number of subjects classified
            self.users[user_id].n_subjects += 1
            # Appending this classification to the subject's and user's histories
            self.subjects[subject_id].classifications.append(cl_row)
            self.users[user_id].classifications.append(cl_row)

    def consensus_analysis(self, n_iterations):
        """
        Performs n_iterations of consensus analysis.
        """
        for n in range(n_iterations):
            self.update_subject_scores()
            self.update_user_weights()
            self.scale_user_weights()

    def update_subject_scores(self):
        """
        Updates the scores of subjects in 'subjects' using the weights of all users in 'users'.
        """
        # Iterating through subjects
        for subject in self.subjects.values():
            # Iterating through this subject's classification history
            for cl in subject.classifications:
                # Getting the user who made the classification
                user = self.users[cl['user_id']]
                # Getting the label submitted by the user
                label = cl['label']
                # Updating the subject's score
                subject.update_score(user, label)

    def update_user_weights(self):
        """
        Updates the weights of users in 'users' using the scores of all subjects in 'subjects'.
        """
        # Iterating through users
        for user in self.users.values():
            # Iterating through this user's classification history
            for cl in user.classifications:
                # Getting the subject that the classification was made on
                subject = self.subjects[cl['subject_id']]
                # Getting the label submitted by the user
                label = cl['label']
                # Updating th user's weight
                user.update_weight(subject, label)

    def scale_user_weights(self):
        """
        Scales all user weights, such that the mean equals 1.
        """
        # Getting a list of User instances
        user_list = list(self.users.values())
        # Getting the total number of users
        n_users = len(user_list)
        # Getting the sum of all users' weights
        user_weight_sum = sum([u.weight for u in user_list])
        # Calculating the average user weight
        avg_user_weight = user_weight_sum / n_users
        # Calculating the scale-factor necessary to make the mean weight equal 1
        user_weight_scalar = avg_user_weight ** (-1)
        # Applying the scale-factor to every user weight
        for user_id in self.users.keys():
            self.users[user_id].weight *= user_weight_scalar

    def update_CSVs(self):
        """
        Rewrites CSVs / manifests with the data in the 'subjects' and 'users' dictionaries.
        """
        # Getting subjects' data in list format
        subject_rows = [s.dump() for s in self.subjects.values()]
        # Getting users' data in list format
        user_rows = [u.dump() for u in self.users.values()]
        # Writing subject/user data to CSVs/manifests
        self.subject_csv.write_rows(subject_rows)
        self.user_csv.write_rows(user_rows)
        self.subject_manifest.write_rows(subject_rows)
        self.user_manifest.write_rows(user_rows)


# THE FUNCTIONS BELOW ARE MEANT TO TEST 'ConsensusAnalysis'

import numpy as np


def write_test_classifications_csv(n_users, n_subjects, cl_per_user, avg_user_correct_rate, stdev_user_correct_rate):
    user_ids = list(range(1, n_users + 1))
    subject_ids = list(range(1, n_subjects + 1))
    user_correct_rates = dict((user_id, max(0.001, np.random.normal(avg_user_correct_rate, stdev_user_correct_rate)))
                              for user_id in user_ids)
    subject_true_labels = dict((subject_id, np.random.choice(['negative', 'tenebrite'], p=[0.9, 0.1]))
                               for subject_id in subject_ids)
    print(subject_true_labels)
    classifications = []
    for i in range(cl_per_user * n_users):
        user_id = np.random.choice(user_ids)
        user_correct_rate = user_correct_rates[user_id]
        subject_id = np.random.choice(subject_ids)
        subject_true_label = subject_true_labels[subject_id]
        label = get_label(user_correct_rate, subject_true_label)
        classifications.append({'classification_id': i,
                                'subject_id': subject_id,
                                'user_id': user_id,
                                'label': label})
    classifications_csv = CsvUtils(consensus_classifications_csv_path, fieldnames_list=list(classifications[0].keys()))
    classifications_csv.write_rows(classifications, dict_writer=True)


def get_label(user_correct_rate, subject_true_label):
    if np.random.uniform() < user_correct_rate:
        label = subject_true_label
    else:
        label = 'negative' if subject_true_label == 'tenebrite' else 'tenebrite'
    return label


def analyze_results():
    import matplotlib.pyplot as plt
    subjects_csv = CsvUtils(consensus_subjects_manifest_csv_path)
    subjects = subjects_csv.read_rows(dict_reader=True)
    subject_ids = [s['subject_id'] for s in subjects]
    subject_scores = [json.loads(s['score']) for s in subjects]
    subject_scores_rounded = []
    for ss in subject_scores:
        for k in ss.keys():
            ss[k] = round(ss[k], 3)
        subject_scores_rounded.append(ss)
    ids_score = list(zip(subject_ids, subject_scores_rounded))
    ids_score = sorted(ids_score, key=lambda t: int(t[0]))
    print(*ids_score, sep='\n')

    users_csv = CsvUtils(consensus_users_manifest_csv_path)
    users = users_csv.read_rows(dict_reader=True)
    user_weights = [round(float(u['weight']), 3) for u in users]
    print('\nuser_weights: ', user_weights)
    print('\tavg: ', round(sum(user_weights) / len(user_weights), 3))

    # plt.hist(user_weights, bins=10)
    # plt.show()


if __name__ == "__main__":

    csv.field_size_limit(sys.maxsize)

    try:
        pass
        os.remove(consensus_classifications_csv_path)
        os.remove(consensus_subjects_manifest_csv_path)
        os.remove(consensus_users_manifest_csv_path)
        os.remove(consensus_subjects_manifest_path)
        os.remove(consensus_users_manifest_path)
    except FileNotFoundError:
        pass

    write_test_classifications_csv(n_users=10,
                                   n_subjects=10,
                                   cl_per_user=5,
                                   avg_user_correct_rate=0.6,
                                   stdev_user_correct_rate=0.2)
    ca = ConsensusAnalysis(cl_csv_path=consensus_classifications_csv_path,
                           subjects_csv_path=consensus_subjects_manifest_csv_path,
                           users_csv_path=consensus_users_manifest_csv_path,
                           subjects_manifest_path=consensus_subjects_manifest_path,
                           users_manifest_path=consensus_users_manifest_path)
    ca.run(n_iterations=1)
    analyze_results()
