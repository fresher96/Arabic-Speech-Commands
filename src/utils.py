import os
from math import ceil
from collections import defaultdict


# Ensure that the current file is a wave file
def is_wav_file(file_name):
    return file_name.lower().endswith('.wav')


# Create a dictionary to match each class_name with its files
def get_dataset_files(dataset_path):
    # Create a dictionary of lists
    dataset_files = defaultdict(list)
    for dir_path, _, file_names in os.walk(dataset_path):
        for file_name in file_names:
            if is_wav_file(file_name):
                class_name = os.path.basename(dir_path)
                dataset_files[class_name].append(file_name)
    return dataset_files


# Group the list of files by person
def group_by_person(files_list):
    person = defaultdict(list)
    for file_name in files_list:
        person[file_name[:8]].append(file_name)
    return list(person.values())


# Dataset splitting: training set, validation set, test set
def split(dataset_path, validation_part=0.2, test_part=0.2):
    dataset_files = get_dataset_files(dataset_path)
    training_files, validation_files, test_files = {}, {}, {}
    for class_name, files_list in dataset_files.items():
        files_lists = group_by_person(files_list)
        num_test = ceil(test_part * len(files_lists))
        num_validation = ceil(validation_part * len(files_lists))
        for i in range(num_test):
            for file_name in files_lists[i]:
                file_path = os.path.join(dataset_path, class_name, file_name)
                test_files[file_path] = class_name
        for i in range(num_test, num_test + num_validation):
            for file_name in files_lists[i]:
                file_path = os.path.join(dataset_path, class_name, file_name)
                validation_files[file_path] = class_name
        for i in range(num_test + num_validation, len(files_lists)):
            for file_name in files_lists[i]:
                file_path = os.path.join(dataset_path, class_name, file_name)
                training_files[file_path] = class_name
    return {'train': training_files, 'val': validation_files, 'test': test_files}

