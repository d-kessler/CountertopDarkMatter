import json

from python.google_drive_folder.google_drive import GoogleDriveUtils
from python.vars.paths_and_ids import staging_ground_folder_drive_id


def main():
    gd = GoogleDriveUtils()
    staging_ground_gfiles = gd.list_gfiles(staging_ground_folder_drive_id, exclude_mime_types=gd.gfolder_mime_type)
    second_folders_dict = {}

    print('Creating a first-folder...')
    date = input("\tMM-DD-YY: ")
    while len(y := date.split('-')) != 3 or len(y[0]) != 2 or len(y[0]) != 2 or len(y[0]) != 2:
        date = input("\t\t Please enter something of the form MM-DD-YY: ")
    image_dimensions = input("\tImage Height x Width (inches): ")
    while len(y := image_dimensions.split('x')) != 2 or not y[0].isdigit() or not y[1].isdigit():
        image_dimensions = input('\t\tPlease enter something of the form (integer)x(integer), ignoring parentheses: ')
    warehouse_name = input('\tWarehouse name: ').title().replace(' ', '')
    warehouse_city = input('\tWarehouse city: ').title()
    warehouse_state = input('\tWarehouse state: ').title()
    first_folder_name = '_'.join([date, image_dimensions, warehouse_name, warehouse_city, warehouse_state])

    gd.create_gfolder(first_folder_name, staging_ground_folder_drive_id)
    first_folder_gfile = gd.get_gfile_instance(staging_ground_folder_drive_id, gfile_name=first_folder_name)

    create_second_folder = 'y'
    print('\tCreating a second-folder... ')
    while create_second_folder == 'y':
        slab_id = input('\t\tSlab ID: ')
        while not slab_id[0].isnumeric() and slab_id[0] != 'u':
            slab_id = input('\t\t\tThe first character must be a number or \'u\'... Slab ID: ')
        granite_type = input('\t\tGranite type: ').title().replace(' ', '')
        columns_or_rows = input('\t\tColumns or rows (eg. c#, r#, or u): ')
        if columns_or_rows[0] != 'u':
            while columns_or_rows[0] not in ('c', 'r') or not columns_or_rows[1:].isnumeric():
                columns_or_rows = \
                    input('\t\t\t Please center something of the form (\'c\' or \'r\')(integer), ignoring parentheses: ')
        second_folder_name = '_'.join([slab_id, granite_type, columns_or_rows])

        gd.create_gfolder(second_folder_name, first_folder_gfile['id'])
        second_folder_gfile = gd.get_gfile_instance(first_folder_gfile['id'], gfile_name=second_folder_name)

        slab_identifiers_folder_name = 'slab_identifiers'
        gd.create_gfolder(slab_identifiers_folder_name, second_folder_gfile['id'])
        slab_identifiers_gfile = gd.get_gfile_instance(second_folder_gfile['id'],
                                                       gfile_name=slab_identifiers_folder_name)

        print('\t\tIn regard to the numbers in the names of the images...')
        slab_identifiers_numbers = eval(input('\t\t\tSlab identifiers\' numbers (comma-separated list): '))
        if type(slab_identifiers_numbers) in (int, str):
            slab_identifiers_numbers = tuple([slab_identifiers_numbers])
        print('\t\t\tIn regard to which image-numbers belong to this second folder...')
        first_image_number = eval(input('\t\t\t\t\tFirst image-number: '))
        first_image_number = correct_input(first_image_number, Type=int, n_tabs=4)
        last_image_number = eval(input('\t\t\t\t\tLast image-number: '))
        last_image_number = correct_input(last_image_number, Type=int, n_tabs=4)

        second_folders_dict[json.dumps(second_folder_gfile)] = \
            {'slab_identifiers_gfile': slab_identifiers_gfile,
             'slab_identifiers_numbers': slab_identifiers_numbers,
             'first_last_image_numbers': (first_image_number, last_image_number)}

        create_second_folder = input('\tCreate a new second-folder? [y/n]: ')
        create_second_folder = correct_input(create_second_folder, options=['y', 'n'])

    for gfile in staging_ground_gfiles:
        if gfile['title'] == "folder_naming_conventions.txt":
            continue
        image_number = get_image_number(gfile['title'])
        for second_folder in second_folders_dict.keys():
            first_image_number, last_image_number = second_folders_dict[second_folder]['first_last_image_numbers']
            if image_number in second_folders_dict[second_folder]['slab_identifiers_numbers']:
                gd.move_gfile(gfile, second_folders_dict[second_folder]['slab_identifiers_gfile']['id'])
            elif first_image_number <= image_number <= last_image_number:
                gd.move_gfile(gfile, json.loads(second_folder)['id'])


def correct_input(given, options=None, Type=None, n_tabs=1):
    tabs = '\t' * n_tabs
    if options:
        while given not in options:
            given = input(tabs + f'Please enter one of {options}: ')
    elif Type:
        while type(given) != Type:
            given = input(tabs + f'Please enter a variable of type {str(Type).upper()}: ')
    return given


def get_image_number(image_name):
    without_extension = image_name.split('.')[0]
    for i in range(1, len(without_extension)):
        if not without_extension[-i].isdigit():
            return int(without_extension[-i + 1:])


if __name__ == '__main__':
    main()
