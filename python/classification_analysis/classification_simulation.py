import numpy as np
import numpy.random as rand
from poibin.poibin import PoiBin


# reformulate: replace 'n' with 0 in labels


def correct_choice(label):
    try:
        return eval(label)
    except ValueError:
        return label
    except NameError:
        return label


class User:
    def __init__(self, user_id, n_cl, subj_seen_dict, intrinsic_correct_rates, approx_correct_rates, label_freqs):
        """
        Zooniverse user.
            user_id = user's unique identification number (int)
            n_cl = user's number of classifications made (int)
            subj_seen_dict = dictionary with key-value pairs:
                'label': number of times the user has seen a training subject of this type
            intrinsic_correct_rates = dictionary with key-value pairs:
                'label': the rate at which the user truly classifies subjects of this type correctly (float);
                         this is the limiting value of their correct rate after many classifications
                         on training images
            approx_correct_rates = dictionary with key-value pairs:
                'label': the rate at which we think the user classifies subjects of this type correctly (float),
                         based on the limited number of classifications that they've made on training
                         images of this type
        """
        self.user_id = user_id
        self.n_cl = n_cl
        self.subj_seen_dict = subj_seen_dict
        self.intrinsic_correct_rates = intrinsic_correct_rates
        self.approx_correct_rates = approx_correct_rates
        self.label_freqs = label_freqs
        self.labels = list(label_freqs.keys())

    def get_label_choice(self):
        """
        Returns a randomly selected label to be submitted on a subject according to the user's aptitude
        for submitting labels of different types.
        """
        return correct_choice(rand.choice(self.labels, p=list(self.label_freqs.values())))


class Subject:
    def __init__(self, subject_id, cls, sim_sizes):
        """
        Zooniverse subject.
            subject_id = subject's unique identification number (int)
            cls = list of 'classifications' made on the subject; classifications dictionaries are of the form:
                {'user': User object of the user that made tha classification,
                 'label': the label that the user submitted}
            sim_sizes = list of simulation sizes on which users have been 'trained', such that we have knowledge
                        of users correct rates with respect to tenebrite of these sizes
        """
        self.subject_id = subject_id
        self.cls = cls
        self.sim_sizes = sim_sizes
        self.tenebrite_pvals = dict((sim_size, 0) for sim_size in sim_sizes)  # see 'self.update_tenebrite_pvals'
        self.update_tenebrite_pvals()

    def update_tenebrite_pvals(self):
        """
        Updates the subject's probability of containing a tenebrite of each simulation size.
        This probability is taken to be the p-value for the number of tenebrite detections being
        greater than or equal to 1 according to the Poisson Binomial Distribution defined by users'
        true-positive and false-negatives rates.
            The Poisson Binomial Distribution is the distribution in the number of successes k among N
        Bernoulli (success/failure) trials, where the probability of success P(success) can vary from
        trial to trial. When a user labels a subject as containing a tenebrite of size S, the probability
        of 'success' (that is, accurate detection of a tenebrite of size S) is that user's true-positive
        rate with respect to size S. If a user labels a subject as negative, the probabilities of success
        with respect to each tenebrite size are the user's false-negative rates with respect to those sizes.
        """
        tenebrite_detection_probabilities = dict((sim_size, []) for sim_size in self.sim_sizes)
        for cl in self.cls:
            user, label = cl.values()
            label_correct_rate = user.approx_correct_rates[label]
            if label != 0:
                tenebrite_detection_probabilities[label].append(label_correct_rate)
            else:
                for sim_size in self.sim_sizes:
                    tenebrite_detection_probabilities[sim_size].append(1 - label_correct_rate)
        for sim_size in self.sim_sizes:
            poisson_binomial = PoiBin(tenebrite_detection_probabilities[sim_size])
            tenebrite_probability = poisson_binomial.pval(number_successes=1)
            self.tenebrite_pvals[sim_size] = tenebrite_probability


class SimulateClassifications:
    def __init__(self, n_users, n_cl_mean, n_cl_stdev,
                 n_subjects, sim_subj_prop, neg_subj_prop,
                 sim_sizes, sim_sizes_props,
                 tpr_means, tpr_stdevs,
                 tnr_mean, tnr_stdev,
                 gamma=1):
        """
        n_users = number of users (integer)
        n_cl_mean = mean number of classifications made by users (integer)
        n_cl_stdev = st. dev. of ^ (float)
        neg_cl_prop_mean = mean proportion of users' classifications that are 'negative' (float)
        neg_cl_prop_stdev = st. dev. of ^ (float)
        n_subjects = number of subjects (integer)
        sim_subj_prop = proportion of subjects that are type 'simulation' (float)
        neg_subj_prop = proportion of subjects that are type 'negative' (float)
        sim_sizes = simulations' semi-minor axis sizes in millimeters (list, eg. [1, 2, 3])
        sim_sizes_props = proportion of simulations of each size (list, eg. [0.5, 0.3, 0.2])
            REMARK: the elements of sim_sizes_props must sum to one.
        label_submit_freqs = list of average frequencies with which users submit each kind of label,
                             that is, 'negative' or 'tenebrite of size X',
                             eg. ( 0.7 (negative freq), 0.2 (size 1 freq), 0.1 (size 2 freq) )
        tpr_means = mean of users' true positive rates WRT each simulation size (list, eg. [0.3, 0.7, 0.9])
        tpr_stdevs = st. dev. of ^ (list, eg. [0.1, 0.2, 0.1])
        tnr_means = analogue of tpr_means for users' true negative rates (float)
        tnr_stdevs = analogue of tpr_stdevs for ^ (float)
        gamma = 'Laplace smoothing parameter' (int)
        """
        self.n_users = n_users
        self.n_cl_mean = n_cl_mean
        self.n_cl_stdev = n_cl_stdev
        self.n_subjects = n_subjects
        self.sim_subj_prop = sim_subj_prop
        self.neg_subj_prop = neg_subj_prop
        self.sim_sizes = sim_sizes
        self.sim_sizes_props = self.sim_sizes_dict(sim_sizes_props)
        self.tpr_means = self.sim_sizes_dict(tpr_means)
        self.tpr_stdevs = self.sim_sizes_dict(tpr_stdevs)
        self.tnr_mean = tnr_mean
        self.tnr_stdev = tnr_stdev
        self.gamma = gamma
        self.labels = [0] + sim_sizes  # 0 <--> 'negative'
        self.users = {}
        self.subjects = {}
        self.cl_per_subj = 0

    def sim_sizes_dict(self, lst):
        return dict((self.sim_sizes[i], lst[i]) for i in range(len(self.sim_sizes)))

    def run(self):
        self.simulate_users()
        self.simulate_subjects()
        for subject in self.subjects.values():
            print(subject.tenebrite_pvals)

    def simulate_users(self):
        # Assigning users IDs ranging from 1 to self.n_users
        for user_id in range(1, self.n_users + 1):
            # Selecting the number of classifications made by the user from the gaussian distribution
            # Note: the minimum classification for users is 1 (any less, and they are not users of the project)
            n_cl = max(1, round(rand.normal(self.n_cl_mean, self.n_cl_stdev)))
            # Initializing a dictionary to track the number of each type of training subject
            # (negatives and simulations of differing semi-minor axis size) are seen by the user
            subj_seen_dict = dict((label, 0) for label in self.labels)
            # Initializing a dictionary to track the user's intrinsic 'correct' rates
            intrinsic_correct_rates = dict((label, 0) for label in self.labels)
            # Initializing a dictionary to track the user's 'approximate' correct rates,
            # which approaches their intrinsic correct rates as they make more classifications
            approx_correct_rates = dict((label, 0) for label in self.labels)
            # Initializing a dictionary to track the frequency with which the user submits each kind of label
            label_freqs = dict((label, 0) for label in self.labels)
            # Filling the above created dicts with information about negative (0) and simulation subjects
            # (# negatives seen) = (# subjects seen, ie. classifications) * (proportion of subjects that are negative)
            subj_seen_dict[0] = round(n_cl * self.neg_subj_prop)
            for sim_size in self.sim_sizes:
                # (# size X) = (# subjects seen, ie. classifications) * (proportion of subjects that are simulations) *
                # (proportion of simulations that are size X)
                subj_seen_dict[sim_size] = round(n_cl * self.sim_subj_prop * self.sim_sizes_props[sim_size])
            if list(subj_seen_dict.values()) == [0] * len(list(subj_seen_dict.values())):
                # Accounting for rounding error, which may lead to subj_seen_dict having all zero values
                # Getting the frequency with which each kind of training subject would be shown to the user
                labels_seen_freqs = [self.neg_subj_prop] + \
                                    [self.sim_subj_prop * self.sim_sizes_props[sim_size] for sim_size in self.sim_sizes]
                # Normalizing
                labels_seen_freqs = [f / sum(labels_seen_freqs) for f in labels_seen_freqs]
                # Selecting as the kind of training subject they saw the one that is shown most frequently
                label_seen = correct_choice(rand.choice(self.labels, p=labels_seen_freqs))
                subj_seen_dict[label_seen] = 1
            # Selecting the intrinsic correct rate for negatives (ie. true-negative rate) from the gaussian distribution
            intrinsic_correct_rates[0] = min(0.99, max(0.01, rand.normal(self.tnr_mean, self.tnr_stdev)))
            # Getting the approximate correct rate for negatives via the method given in 'self.get_approx_rate'
            approx_correct_rates[0] = self.get_approx_rate(subj_seen_dict[0], intrinsic_correct_rates[0])
            # Getting the approximate frequency with which this user submits 'negative' labels
            label_freqs[0] = approx_correct_rates[0]
            for sim_size in self.sim_sizes:
                # Selecting the intrinsic correct rate for simulations (ie. true-positive rate) from the gaussian distribution
                intrinsic_correct_rates[sim_size] = min(
                    0.99, max(0.01, rand.normal(self.tpr_means[sim_size], self.tpr_stdevs[sim_size])))
                # Getting the approximate correct rate for simulations via the method given in 'self.get_approx_rate'
                approx_correct_rates[sim_size] = self.get_approx_rate(subj_seen_dict[sim_size],
                                                                      intrinsic_correct_rates[sim_size])
                # Getting the approximate frequency with which this user submits this kind of label
                label_freqs[sim_size] = (1 - approx_correct_rates[0]) / len(self.sim_sizes)
            # Appending to self.users a User object whose attributes are the parameters just calculated
            self.users[user_id] = User(
                user_id, n_cl, subj_seen_dict, intrinsic_correct_rates, approx_correct_rates, label_freqs)

    def get_approx_rate(self, n_cl, correct_rate):
        """
        Gets the approximate 'correct' rate of a user for a particular type of training image by assuming
        that the probability of a correct classification is equivalent to their intrinsic correct rate;
        for a number of classifications equivalent to n_cl, the rejection method is used with respect to
        a 'correct_rate' to determine whether or not this classification should be treated as correct.
        The approximate correct rate is then obtained by dividing the number of correct classifications
        by n_cl and applying 'Laplace' smoothing to down-weight the rates of inexperienced users, as is
        done in (k)SWAP.
            n_cl = number of classifications made by the user on this type of training image
            correct_rate = the user's correct rate for this type of training image
        """
        n_correct = 0
        for i in range(n_cl):
            if rand.uniform() < correct_rate:
                n_correct += 1
        approx_correct_rate = (n_correct + self.gamma) / (n_cl + 2 * self.gamma)
        return approx_correct_rate

    def simulate_subjects(self):
        # Calculating the total number of classifications made by users
        total_n_cl = sum([user.n_cl for user in self.users.values()])
        # Approximating the average number of classifications made per subject
        self.cl_per_subj = round(total_n_cl / self.n_subjects)
        # Getting a list of simulated users' IDs
        user_ids = list(self.users.keys())
        # Assigning subjects IDs ranging from 1 to self.n_subjects
        for subject_id in range(1, self.n_subjects + 1):
            cls = []  # list of classifications made on the subject specified by subject_id
            # Iterating through supposed classifications made on the subject,
            # the number of iterations equal to self.cl_per_subj
            for cl in range(self.cl_per_subj):
                # Randomly selecting a simulated user to be the author of this classification
                user = self.users[int(rand.choice(user_ids))]
                # Randomly selecting the 'label' that the user submits, according to how often they have previously
                # submitted each kind of label (eg. 'negative' and simulations of differing semi-minor axis size)
                label = user.get_label_choice()
                # Appending this classification to the list of ones by on the subject
                cls.append({'user': user, 'label': label})
            # Appending to self.subjects a Subject objects with attributes the variables just obtained
            self.subjects[subject_id] = Subject(subject_id, cls, self.sim_sizes)


if __name__ == '__main__':
    sc = SimulateClassifications(
        n_users=10, n_cl_mean=10, n_cl_stdev=5,
        n_subjects=10, sim_subj_prop=0.3, neg_subj_prop=0.2,
        sim_sizes=[2, 3, 4], sim_sizes_props=[0.4, 0.3, 0.3],
        tpr_means=[0.3, 0.4, 0.5], tpr_stdevs=[0.1, 0.1, 0.1],
        tnr_mean=0.6, tnr_stdev=0.2,
        gamma=1
    )
    sc.run()
