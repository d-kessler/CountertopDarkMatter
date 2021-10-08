
def get_numerical_class_vars(Class):
    Class_dict = dict(Class.__dict__)
    to_pop = []
    for k in Class_dict.keys():
        if type(Class_dict[k]) not in (int, float):
            to_pop.append(k)
    [Class_dict.pop(k) for k in to_pop]
    return Class_dict
