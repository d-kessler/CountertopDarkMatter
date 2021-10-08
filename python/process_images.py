import os
import json
import time
import numpy as np
from datetime import date
from shutil import copyfile

from python.utils.exif_utils import ImageExif
from python.utils.git_utils import push_files_to_GitHub
from python.utils.misc_utils import get_numerical_class_vars
from python.utils.cv_utils import get_grain_stats, get_glare_area
from python.google_drive_folder.google_drive import GoogleDriveUtils
from python.utils.zooniverse_utils import upload_subjects_to_zooniverse
from python.utils.csv_excel_utils import CsvUtils, ExcelUtils, verify_dict
from python.utils.ellipse_utils import SimUtils, resize_ellipse_dimensions
from python.utils.image_utils import configure_pil_image, get_mm_per_pixel, resize_to_limit, draw_scale_bars
from python.utils.file_utils import get_file_names, get_extension, get_subfolder_names, make_folder, clear_folder

from python.vars.fieldnames import experiment_fieldnames, simulation_fieldnames, processed_folders_fieldnames, \
    processed_slabs_fieldnames
from python.vars.subject_parameters import min_shorter_image_dimension_in, min_longer_image_dimension_in, \
    scale_bar_length_mm, scale_bar_width_mm, scale_bars_color, scale_bars_min_number, \
    scale_bars_perpendicular_buffer, scale_bars_parallel_buffer, scale_bar_edge_color, scale_bars_edge_with, \
    simulations_per_second_folder, min_sim_minor_axis_mm, max_sim_minor_axis_mm, sim_minor_axis_step_mm, \
    max_sim_major_axis_mm,  min_sim_edge_poly_rad_mm, max_sim_edge_poly_rad_mm, min_sim_edge_poly_sides, \
    max_sim_edge_poly_sides
from python.vars.project_info import experiment_subject_set_id, simulation_subject_set_id, simulation_feedback_id
from python.vars.paths_and_ids import unprocessed_images_zeroth_folder, experiment_subjects_folder, experiment_csv_path, \
    simulation_subjects_folder, simulation_csv_path, experiment_manifest_path, experiment_manifest_csv_path, \
    simulation_manifest_path, simulation_manifest_csv_path, name_id_manifest_path, name_id_manifest_csv_path, \
    processed_folders_manifest_path, processed_folders_manifest_csv_path, processed_slabs_manifest_path, \
    processed_slabs_manifest_csv_path

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir(os.path.join(".."))

"""
NOTE: Before attempting to upload images to Zooniverse from a new computer, enter into the command line
                                    "panoptes configure" ,
then enter a collaborator's Zooniverse username and password (the password text will be hidden).
"""


class FirstFolder:
    def __init__(self, name):
        """
        Correspond to local subfolders of 'data/images'.
            name: local name of the folder
        """
        self.name = name
        self.correct_name()
        self.path = os.path.join(unprocessed_images_zeroth_folder, self.name)
        self.date, self.uncropped_image_dimensions_in, self.warehouse, self.location = self.parse_name()
        # Remark: if images are not large enough to be cropped, uncropped_image_dimensions_in equals image_dimensions_in
        self.image_dimensions_in, self.image_dimensions_mm, self.cropping_necessary = self.configure_image_dimensions()
        self.second_folders = {}

    def correct_name(self):
        """
        Ensures that the given name accords with conventions.
        """
        original_name = self.name
        # While the folder name is incorrect, ask for user input
        while self.named_correctly() is False:
            self.input_name()
        # If the original name was not correct, rename the local folder
        if self.name != original_name:
            original_path = os.path.join(unprocessed_images_zeroth_folder, original_name)
            corrected_path = os.path.join(unprocessed_images_zeroth_folder, self.name)
            os.rename(original_path, corrected_path)

    def named_correctly(self):
        """
        Returns a Boolean telling whether the first folder's name accords with conventions. May make slight
        alterations to the name (ie. removing spaces).
            MM-DD-YY_HeightxWidth_WarehouseName_WarehouseCity_WarehouseState
        """
        # Checking whether all components were given
        components = self.name.split("_")
        components_length_correct = (len(components) == 5)
        if components_length_correct is False:
            return False
        # Checking whether each component of MM-DD-YY is a two-digit integer
        date_components = components[0].split('-')
        date_components_correct = ([c.isdigit() and (len(c) == 2) for c in date_components] == [True] * 3)
        if date_components_correct is False:
            return False
        # Checking whether each component of Height x Width is a number
        dimension_components = components[1].split('x')
        dimension_components_correct = ([isfloat(c) for c in dimension_components] == [True] * 2)
        if dimension_components_correct is False:
            return False
        # Checking whether the name contains spaces
        no_spaces = (' ' not in self.name)
        if no_spaces is False:
            # Deleting any spaces present
            self.name = self.name.replace(' ', '')
        # If all checks are passed, return True
        return True

    def input_name(self):
        """
        Gets the corrected name via user input.
        """
        self.name = input(f'First folder {self.name} is named incorrectly.'
                          '\nThe correct format is: MM-DD-YY_HeightxWidth_WarehouseName_WarehouseCity_WarehouseState'
                          '\n\tWhere HeightxWidth is the height and width dimensions of the image in inches, '
                          'separated by "x"'
                          '\n\tInput the correct name: ')

    def parse_name(self):
        """
        Parses the first folder's name for the following properties of the images that it contains:
        date taken, physical dimensions in inches, warehouse name, and warehouse location (city, state).
        """
        date, image_dimensions_in_str, warehouse, city, state = self.name.split('_')
        # Converted image dimensions to integers and placing in a dictionary for ease of reference
        image_dimensions_in_list = [int(d) for d in image_dimensions_in_str.split('x')]
        image_dimensions_in = {'height': image_dimensions_in_list[0], 'width': image_dimensions_in_list[1]}
        # Joining warehouse city and warehouse state strings into single 'location' string
        location = ', '.join([city, state])
        return date, image_dimensions_in, warehouse, location

    def configure_image_dimensions(self):
        """
        Configures the physical dimensions of the images in the first folder and determines the necessity of cropping;
        an image will be cropped in four parts, such that each of its original dimensions are halved, if it satisfies:
            shorter dimension > 2 * minimum shorter dimension, and
            longer dimension > 2 * minimum longer dimension
        If the above is satisfied and the images in this folder will therefore be cropped, the function returns
        the dimensions of the to-be-created cropped images.
        """
        # Getting the image dimensions in inches (in.) from the name of the first folder
        image_dimensions_in_list = list(self.uncropped_image_dimensions_in.values())
        # Determining the necessity of cropping the images from their size relative to the minimum allowable dimensions
        cropping_necessary = \
            (min(image_dimensions_in_list) > 2 * min_shorter_image_dimension_in) and \
            (max(image_dimensions_in_list) > 2 * min_longer_image_dimension_in)
        # If cropping, setting the image dimensions to be those of the to-be-created cropped images
        if cropping_necessary:
            image_dimensions_in_list = [int(d / 2) for d in image_dimensions_in_list]
        # Converting the image dimensions to millimeters
        image_dimensions_mm_list = [d * 25.4 for d in image_dimensions_in_list]
        # Putting image dimensions in a dict for ease of reference
        image_dimensions_in = {'height': image_dimensions_in_list[0], 'width': image_dimensions_in_list[1]}
        image_dimensions_mm = {'height': image_dimensions_mm_list[0], 'width': image_dimensions_mm_list[1]}
        return image_dimensions_in, image_dimensions_mm, cropping_necessary


class SecondFolder:
    def __init__(self, name, first_folder, tally_area=True):
        """
        Correspond to local subfolders of a 'first folder'.
            name: local name of the folder
            first_folder: FirstFolder instance of parent folder
            tally_area: Flag determining whether this the area of the images in this
                second folder can be counted towards the total slab area examined
        """
        self.name = name
        self.first_folder = first_folder
        self.tally_area = tally_area
        # Ensuring that the given name accords with conventions
        self.correct_name()
        self.path = os.path.join(first_folder.path, self.name)
        # Parsing the name for the data therein
        self.slab_id, self.granite_type, self.cols_or_rows, self.n_cols_or_rows = self.parse_name()
        # Getting a list of UnprocessedImage instances for each image in the second folder
        self.cropping_necessary = self.first_folder.cropping_necessary
        self.unprocessed_images = self.get_unprocessed_images()
        # If necessary, cropping each image in the second folder, saving to newly defined 'cropped_folder_path'
        if self.cropping_necessary:
            self.cropped_folder_path = os.path.join(self.path, 'cropped')
            self.cropped_images = self.crop_images()
        # Determining the slab-locations of the images in the second folder
        self.name_position_dict = self.get_name_position_dict()
        # Initializing variables to track the IDs of the first and last experiment and simulation subjects made from
        # the images contained in this second folder
        self.experiment_id_endpoints = []
        self.simulation_id_endpoints = []

    def correct_name(self):
        """
        Ensures that the given name accords with conventions.
        """
        original_name = self.name
        # While the folder name is incorrect, ask for user input
        while self.named_correctly() is False:
            self.input_name()
        # If the original name was not correct, rename the local folder
        if self.name != original_name:
            original_path = os.path.join(self.first_folder.path, original_name)
            corrected_path = os.path.join(self.first_folder.path, self.name)
            os.rename(original_path, corrected_path)

    def named_correctly(self):
        """
        Returns a Boolean telling whether the second folder's name accords with conventions (below). May make slight
        alterations to the name (ie. removing spaces or illegal characters).
            SlabID_GraniteType_NumberOfColumnsOrRows
                where SlabID's components are separated by '-' (dash) and NumberOfColumnsOrRows is of the form:
                    "c#" for columns, "r#" for rows, or 'u' for unknown
        """
        # Checking whether all components were given
        components = self.name.split("_")
        components_length_correct = (len(components) == 3)
        if components_length_correct is False:
            return False
        slab_id, granite_type, number_columns_or_rows = components
        # Checking for illegal characters in SlabID
        slab_id_correct = ([c.isalnum() or c == '-' for c in slab_id] == [True] * len(slab_id))
        if slab_id_correct is False:
            # Replacing any illegal characters found
            slab_id = ''.join(c if c.isalnum() else '-' for c in slab_id)
            self.name = '_'.join([slab_id, granite_type, number_columns_or_rows])
        # Checking whether NumberOfColumnsOrRows is of the correct format
        number_columns_or_rows_correct = (
                'c' in (y := number_columns_or_rows) and y.split('c')[-1].isdigit()
                or 'r' in y and y.split('r')[-1].isdigit()
                or 'u' in y)
        if number_columns_or_rows_correct is False:
            return False
        # Checking whether the name contains spaces
        no_spaces = (' ' not in self.name)
        if no_spaces is False:
            # Deleting any spaces present and returning the correct second folder name
            self.name = self.name.replace(' ', '')
        # If all checks are passed, return True and the name passed as the correct name
        return True

    def input_name(self):
        """
        Gets the corrected name via user input.
        """
        self.name = input(f'Second folder {self.name} is named incorrectly.'
                          '\nThe correct format is: SlabID_GraniteType_NumberOfColumnsOrRows '
                          '\n\twhere SlabIDs components are separated by "-" (dash) and NumberOfColumnsOrRows '
                          'is of the form: '
                          '\n\t\t"c#" for columns, "r#" for rows, or "u" for unknown'
                          '\n\tInput the correct name: ')

    def parse_name(self):
        """
        Parses the second folder's name for the following information about the slab imaged:
        the slab's ID, the slab's granite type, whether images were taken in columns or rows,
        and the number of image columns or rows.
        """
        slab_id, granite_type, columns_or_rows = self.name.split('_')
        if 'c' in columns_or_rows:
            cols_or_rows = 'columns'
        elif 'r' in columns_or_rows:
            cols_or_rows = 'rows'
        else:
            cols_or_rows = None
        if cols_or_rows:
            n_cols_or_rows = int(columns_or_rows.split(cols_or_rows[0])[-1])
        else:
            n_cols_or_rows = None
        return slab_id, granite_type, cols_or_rows, n_cols_or_rows

    def get_unprocessed_images(self):
        """
        Returns a list of UnprocessedImage instances for the images (not edited since taken) in the second folder.
        """
        unprocessed_images_names = self.get_unprocessed_images_names()
        return [UnprocessedImage(name, self) for name in unprocessed_images_names]

    def get_unprocessed_images_names(self):
        """
        Returns a list of the names of the images in the second folder.
        """
        return get_file_names(self.path, 'images')

    def crop_images(self):
        """
        Crops images in the second folder into four parts, creates and saves images to 'self.cropped_folder_path'.
        """
        # Creating a folder at 'self.cropped_folder_path'
        make_folder(self.cropped_folder_path, clear_existing=True)
        # Initializing a list of CroppedImage instances
        cropped_images = []
        for unprocessed_image in self.unprocessed_images:
            # Getting the unprocessed pixel dimensions, halving them to the get pixel dimensions of the cropped images
            width, height = unprocessed_image.pil_img.size
            cropped_width, cropped_height = int(width / 2), int(height / 2)
            # Storing the x-min, y-min, x-max, y-max values corresponding to the unprocessed image's quadrants in a dict
            quadrant_extrema = {'TL': (0, 0, cropped_width, cropped_height),  # top left
                                'TR': (cropped_width, 0, width, cropped_height),  # top right
                                'BR': (cropped_width, cropped_height, width, height),  # bottom right
                                'BL': (0, cropped_height, cropped_width, height)}  # bottom left
            # Looping through the quadrants
            for quadrant in quadrant_extrema.keys():
                # Getting the quadrant's x-min, y-min, x-max, y-max values, cropping the unprocessed image
                extrema = quadrant_extrema[quadrant]
                cropped_image = unprocessed_image.pil_img.crop(extrema)
                # Saving the cropped image to the 'cropped' folder with the unprocessed image's exif data and name the
                # same as the unprocessed image, but for the addition of the suffix '_(quadrant)'
                extension = get_extension(unprocessed_image.path)
                cropped_image_name = unprocessed_image.name.replace(extension, f'_{quadrant}{extension}')
                cropped_image_path = os.path.join(self.cropped_folder_path, cropped_image_name)
                cropped_image.save(cropped_image_path, exif=unprocessed_image.pil_exif)
                cropped_images.append(CroppedImage(cropped_image_name, cropped_image_path, unprocessed_image))
        return cropped_images

    def get_name_position_dict(self):
        """
        Returns a dictionary with key-value paris '(name)': (slab position), where 'slab position' are the coordinates
        (row, column) of 'name' with respect to the grid defined by the centers of the images taken on the slab,
        with the first coordinate being (1,1) at the top-left of the slab, columns increasing to the right and the
        rows increasing downwards. (Assumes that the photographer snaked downwards, starting from the top-left)
        """

        def iterate_col(row0, col0):
            """
            If row0 is odd, add 1 to col0; if row0 is even, subtract 1 from col0.
            """
            if row0 % 2 == 1:
                col = col0 + 1
            else:
                col = col0 - 1
            return row0, col

        def iterate_row(row0, col0):
            """
            If col0 is odd, add 1 to row0; if col0 is even, subtract 1 from row0.
            """
            if col0 % 2 == 1:
                row = row0 + 1
            else:
                row = row0 - 1
            return row, col0

        # Initializing the dictionary with key-value pairs '(name)': (slab position)
        name_position_dict = {}
        # Getting the appropriate image class instances
        images = self.cropped_images if self.cropping_necessary else self.unprocessed_images
        # Getting variables regarding how images were taken
        cols_or_rows = self.cols_or_rows
        n_cols_or_rows = self.n_cols_or_rows
        # If the number or columns or rows were not given, set all positions to a tuple of empty strings
        if n_cols_or_rows is None:
            for image in images:
                name_position_dict[image.name] = ('', '')
            return name_position_dict
        # Setting the initial coordinate to be (1, 1) and initializing an indexing variable for cropped images
        row, col, crop_index = 1, 1, 0
        # Iterating through images, assigning each an unprocessed image index
        for index, image in enumerate(images):
            # Assigning the first image the initial coordinates
            if index == 0:
                name_position_dict[image.name] = (1, 1)
                continue
            # If we are iterating through cropped images, increment the crop index
            if self.cropping_necessary:
                crop_index += 1
            # Assigning ever bunch of 4 cropped images (which all correspond to the same unprocessed image) the same
            # slab position
            if crop_index % 4 != 0:
                name_position_dict[image.name] = (row, col)
                continue
            # If images were taken in columns...
            if cols_or_rows == 'columns':
                # If the present column is not yet complete, move vertically (within the same column)
                if index % n_cols_or_rows != 0:
                    row, col = iterate_row(row, col)
                # If the present column has been completed, move horizontally (to the next column)
                else:
                    row, col = row, col + 1
            # If images were taken in rows...
            elif cols_or_rows == 'rows':
                # If the present row is not yet complete, move horizontally (within the same row)
                if index % n_cols_or_rows != 0:
                    row, col = iterate_col(row, col)
                # If the present row has been completed, move vertically (to the next row)
                else:
                    row, col = row + 1, col
            # Append the image's name and location to the dictionary initialized above
            name_position_dict[image.name] = (row, col)
        return name_position_dict


class UnprocessedImage:
    def __init__(self, name, second_folder):
        self.name = name
        self.second_folder = second_folder
        self.path = os.path.join(second_folder.path, name)
        if not second_folder.cropping_necessary:
            self.dimensions_mm = second_folder.first_folder.image_dimensions_mm
            self.mm_per_pixel = get_mm_per_pixel(self.path, self.dimensions_mm['height'])
        self.pil_img, self.pil_exif = configure_pil_image(self.path)
        self.lat_long_exif, self.date_exif = self.get_exif()

    def get_exif(self):
        """
        Returns the image's GPS and date exif data if they were recorded.
        """
        image_exif = ImageExif(self.path)
        return (image_exif.get_gps_exif()), image_exif.get_date_exif()


class CroppedImage:
    def __init__(self, name, path, unprocessed_image):
        self.name = name
        self.path = path
        self.unprocessed_image = unprocessed_image
        self.dimensions_mm = unprocessed_image.second_folder.first_folder.image_dimensions_mm


def draw_scale_bars_default_params(path, mm_per_pixel):
    """
    Draws scale bars along all four sides of the image using the parameters found in 'subject_parameters.py'.
        path: path to the image on which scale bars will be drawn
        mm_per_pixel: the millimeter per pixel scale of the image
        return_area: if True, returns the total area occupied by the scale bars in square millimeters
    """
    scale_bar_length_pix = int(scale_bar_length_mm / mm_per_pixel)
    scale_bar_width_pix = int(scale_bar_width_mm / mm_per_pixel)
    max_number = draw_scale_bars(
        path, scale_bar_length_pix, scale_bar_width_pix, scale_bars_color, scale_bars_min_number,
        scale_bars_parallel_buffer, scale_bars_perpendicular_buffer, scale_bar_edge_color, scale_bars_edge_with,
        return_max_number=True)
    # Calculating the slab area occupied by scale bars
    scale_bar_area_pixSq = scale_bar_length_pix * scale_bar_width_pix * (scale_bars_min_number + max_number)
    scale_bar_area_mmSq = scale_bar_area_pixSq * (mm_per_pixel ** 2)  # ~ 22
    return scale_bar_area_mmSq, max_number


class ExperimentSubject:
    def __init__(self, experiment_id, pre_image, scale_bars=False):
        """
        Correspond to 'experiment' Zooniverse subjects (whose classifications are not known to us in advance of their
        classification by users).
            experiment_id: unique integer that identifies the experiment subject amongst other experiment subjects
                           (equals 1 plus the number of existing experiment subjects at the time of this one's addition)
            pre_image: a class instance (UnprocessedImage or CroppedImage) corresponding to the image from which the
                       experiment subject will be made
            scale_bars: True if scale bars should be drawn along the sides of the image, False if not
        """
        self.experiment_id = experiment_id
        self.pre_image = pre_image
        self.scale_bars = scale_bars
        # Assigning a subject ID equal to the experiment ID with the prefix 'e'
        self.subject_id = 'e' + str(experiment_id)
        # Getting the class of 'pre_image' (UnprocessedImage or CroppedImage)
        self.pre_image_class = type(pre_image).__name__
        # Getting the pre_image's corresponding UnprocessedImage instance (either pre_image itself or one of its attributes)
        self.unprocessed_image = self.get_unprocessed_image()
        # Getting SecondFolder and FirstFolder instances
        self.second_folder = self.unprocessed_image.second_folder
        self.first_folder = self.second_folder.first_folder
        # Getting the pre_image's dimensions
        self.dimensions_mm = self.first_folder.image_dimensions_mm
        # Getting the pre_image's corresponding CroppedImage instance (either pre_image itself or None)
        self.cropped_image = self.get_cropped_image()
        # Getting the path of the pre_image
        self.pre_path = y.path if (y := self.cropped_image) else self.unprocessed_image.path
        # Assigning a name to the experiment subject, according to conventions (see assign_name)
        self.name = self.assign_name()
        # Specifying the path to the experiment-subject-to-be
        self.path = os.path.join(experiment_subjects_folder, self.name)
        # Initializing a metadata dictionary for the experiment subject
        self.metadata_dict = self.initialize_metadata_dict()

    def get_unprocessed_image(self):
        """
        Returns the instance of UnprocessedImage from which the subject will be made.
        """
        if self.pre_image_class == 'UnprocessedImage':
            return self.pre_image
        elif self.pre_image_class == 'CroppedImage':
            return self.pre_image.unprocessed_image

    def get_cropped_image(self):
        """
        If the unprocessed image was cropped, returns the CroppedImage instance from which the subject will be made;
        otherwise, returns None.
        """
        if self.pre_image_class == 'CroppedImage':
            return self.pre_image
        else:
            return None

    def assign_name(self):
        """
        Returns the name of the subject, assigned according to the convention:
        (subject id; 'e' + experiment id)_(slab id)_(slab row)_(slab_column)_
            (quadrant, if cropped)_(warehouse name)_(location; city, state)
        """
        extension = get_extension(self.pre_image.name)
        dimensions_in = [str(round(d / 25.4, 1)) for d in self.dimensions_mm.values()]
        row, col = self.second_folder.name_position_dict[self.pre_image.name]
        quadrant = y.name.split('_')[-1] if (y := self.cropped_image) else ''
        return '_'.join([
            self.subject_id, 'x'.join(dimensions_in), self.second_folder.slab_id, str(row), str(col), quadrant,
            self.first_folder.warehouse, self.first_folder.location.replace(', ', '_')]) + extension

    def initialize_metadata_dict(self):
        """
        Initializes the class metadata dictionary with information from the pre-experiment and unprocessed images,
        the first and second folders in which they are contained, and the experiment subject attributes already assigned.
        """
        metadata_dict = dict((fieldname, None) for fieldname in experiment_fieldnames)
        metadata_dict['!subject_id'] = self.subject_id
        metadata_dict['#file_name'] = self.name
        metadata_dict['#second_folder'] = self.second_folder.name
        metadata_dict['#first_folder'] = self.first_folder.name
        metadata_dict['#pre_file_name'] = self.pre_image.name
        metadata_dict['#warehouse'] = self.first_folder.warehouse
        metadata_dict['#location'] = self.first_folder.location
        metadata_dict['#granite_type'] = self.second_folder.granite_type
        metadata_dict['#slab_id'] = self.second_folder.slab_id
        metadata_dict['#date'] = y if (y := self.unprocessed_image.date_exif) else self.first_folder.date
        metadata_dict['#lat_long'] = self.unprocessed_image.lat_long_exif
        metadata_dict['#columns_or_rows'] = self.second_folder.cols_or_rows + str(self.second_folder.n_cols_or_rows)
        metadata_dict['#image_dimensions(in)'] = self.first_folder.image_dimensions_in
        return metadata_dict

    def create(self):
        """
        Creates the experiment subject, by copying the pre-experiment image to the experiment subjects folder,
        resizing the image to the Zooniverse-recommended limit of 600KB, drawing scale bars (if scale bars is True),
        and recording metadata, such as how much of the image's area can be counted towards the tally of total slab
        area examined.
        """
        # Copying the pre-experiment image to the 'experiment_subjects' folder, renaming accordingly
        copyfile(self.pre_path, self.path)
        # Resizing the image to the Zooniverse-recommended 600 KB, getting the factor by which the image's pixel
        # dimensions were resized
        resize_factor = resize_to_limit(self.path, size_limit=600000, return_resize_factor=True)
        # Getting the millimeter per pixel scale of the image (now resized)
        mm_per_pixel = get_mm_per_pixel(self.path, self.dimensions_mm['height'])
        # Getting statistics about the dark-colored grains in the image
        grain_density, grain_stats = get_grain_stats(self.path, mm_per_pixel)
        # Getting the total area (square millimeters) of the image covered by glare
        glare_area_mmSq = get_glare_area(self.path, mm_per_pixel)
        # Drawing scale bars, if specified
        scale_bar_area_mmSq, scale_bar_parameters = 0, {}
        if self.scale_bars is True:
            scale_bar_area_mmSq, max_number = draw_scale_bars_default_params(self.path, mm_per_pixel)
            scale_bar_parameters = {
                'length': scale_bar_length_mm,
                'width': scale_bar_width_mm,
                'min_number': scale_bars_min_number,
                'max_number': max_number,
                'total_area': scale_bar_area_mmSq}
        # Getting the total area of the image that can be counted towards the total slab area examined
        countable_area_mmSq = 0  # if otherwise specified, this image's are is not counted towards the total
        if self.second_folder.tally_area is True:
            # Counting all area not obscured by glare or scale bars
            countable_area_mmSq = (self.dimensions_mm['height'] * self.dimensions_mm['width']) \
                - (glare_area_mmSq + scale_bar_area_mmSq)
        # Adding the above-gotten information to the class metadata dictionary
        self.metadata_dict['#resize_factor'] = resize_factor
        self.metadata_dict['#grain_density'] = grain_density
        self.metadata_dict['#grain_stats(mm)'] = grain_stats
        self.metadata_dict['#glare_area(mm^2)'] = glare_area_mmSq
        self.metadata_dict['#countable_area(mm^2)'] = countable_area_mmSq
        self.metadata_dict['#scale_bar_parameters(mm)'] = scale_bar_parameters

    def dump(self):
        """
        Returns the class metadata dictionary in a form amenable to being written into CSVs and .xlsx files;
        checks whether all wanted and no unwanted metadata was given.
        """
        # Copying the class metadata dictionary, so as not to alter it
        dict_to_dump = self.metadata_dict.copy()
        # Converting the dictionary's dictionaries into strings
        dict_to_dump['#image_dimensions(in)'] = json.dumps(dict_to_dump['#image_dimensions(in)'])
        dict_to_dump['#grain_stats(mm)'] = json.dumps(dict_to_dump['#grain_stats(mm)'])
        dict_to_dump['#scale_bar_parameters(mm)'] = json.dumps(dict_to_dump['#scale_bar_parameters(mm)']) if \
            dict_to_dump['#scale_bar_parameters(mm)'] else ''
        # Checking whether all metadata field in the class dictionary were filled and none were added,
        # ignoring the '#scale_bar_parameters(mm)' which will be intentionally unfilled when scale bars are not drawn
        verify_dict(dict_to_dump, 'experiment', experiment_fieldnames, ignore_keys=['#scale_bar_parameters(mm)'])
        return dict_to_dump


class SimulationSubject:
    def __init__(self, simulation_id, experiment_subject):
        self.simulation_id = simulation_id
        self.experiment_subject = experiment_subject
        # Assigning a subject ID equal to the simulation ID with the prefix 's'
        self.subject_id = 's' + str(simulation_id)
        # Assigning a name to the simulation subject, by prefixing the experiment subject's name with its subject ID
        self.name = self.subject_id + '_' + experiment_subject.name
        # Specifying the path to the simulation-subject-to-be
        self.path = os.path.join(simulation_subjects_folder, self.name)
        # Initializing a metadata dictionary for the simulation subject
        self.metadata_dict = self.initialize_metadata_dict()
        # Copying the experiment image to the 'simulation_subjects' folder, renaming accordingly
        copyfile(self.experiment_subject.path, self.path)
        # Getting the image's millimeter per pixel ratio
        self.mm_per_pixel = get_mm_per_pixel(self.path, self.experiment_subject.dimensions_mm['height'])
        # Initializing dictionaries for the simulated ellipse's dimensions (center pixel coordinates, semi-axes lengths
        # in millimeters, and clockwise rotation in degrees) and 'appearance parameters' (parameters that determine the
        # extent of the image manipulations performed)
        self.ellipse_dimensions = {}
        self.appearance_parameters = {}

    def initialize_metadata_dict(self):
        """
        Initializes the class metadata dictionary with static variable, variable defined in 'subject_parameters.py',
        and simulation subject attributes already assigned.
        """
        metadata_dict = dict((fieldname, None) for fieldname in simulation_fieldnames)
        metadata_dict['!subject_id'] = self.subject_id
        metadata_dict['#file_name'] = self.name
        metadata_dict['#training_subject'] = True  # signal to Panoptes
        metadata_dict['#feedback_1_id'] = simulation_feedback_id
        return metadata_dict

    def create(self):
        """
        Creates the simulation subject, by copying the experiment image to the simulation subjects folder,
        drawing the simulation using the class-variables of SimUtils and variables defined in 'subject_parameters.py',
        and recording the simulation's dimensions and parameters.
        """
        # Drawing the simulation using 'SimUtils', its class-variables, and the variables defined in 'subject_parameters'
        sim_utils = SimUtils(
            granite_image_path=self.path,
            destination_image_path=self.path,
            mm_per_pixel=self.mm_per_pixel,
            minor_axis_min=min_sim_minor_axis_mm,
            minor_axis_max=max_sim_minor_axis_mm,
            minor_axis_step=sim_minor_axis_step_mm,
            major_axis_selection="distribution",
            major_axis_max=max_sim_major_axis_mm,
            poly_rad_min=min_sim_edge_poly_rad_mm,
            poly_rad_max=max_sim_edge_poly_rad_mm,
            poly_sides_min=min_sim_edge_poly_sides,
            poly_sides_max=max_sim_edge_poly_sides,
            circle=True)  # TODO: delete
        sim_utils.draw_sim()
        # Ensuring that scale bars (if present) were not drawn over
        if self.experiment_subject.scale_bars is True:
            draw_scale_bars_default_params(self.path, self.mm_per_pixel)
        # Ensuring that the image's size is less than the Zooniverse-mandated 1MB limit
        resize_factor = resize_to_limit(self.path, size_limit=1e6, return_resize_factor=True)
        # Updating the image's millimeter per pixel scale
        self.mm_per_pixel = get_mm_per_pixel(self.path, self.experiment_subject.dimensions_mm['height'])
        # Getting the ellipses dimensions, adjusted according to the amount by which the image was resized;
        # the parameters of the ellipses marked by users are with respect to the resized image, so it is
        # necessary that we know the ellipse's actual parameters with respect to the resized image
        center_coordinates, axes_lengths_pix, angle = resize_ellipse_dimensions(
            sim_utils.center_coordinates, sim_utils.axes_lengths, sim_utils.angle, resize_factor)
        # Recording the simulated ellipse's dimensions in a class dictionary; axes_lengths are recorded in millimeters
        self.ellipse_dimensions['center_coordinates'] = center_coordinates
        self.ellipse_dimensions['axes_lengths'] = tuple([round(a * self.mm_per_pixel, 2) for a in axes_lengths_pix])
        self.ellipse_dimensions['angle'] = angle
        self.ellipse_dimensions['major_to_minor_ratio'] = round(max(axes_lengths_pix) / min(axes_lengths_pix), 3)
        # Getting the simulation's 'appearance parameters' which determine the image manipulations performed
        self.appearance_parameters = get_numerical_class_vars(SimUtils)
        self.appearance_parameters.update(get_numerical_class_vars(sim_utils))
        # Adjusting lengths according to the amount by which the image was resized and reverting to millimeters
        #   Edge polygon radii
        self.appearance_parameters['poly_rad_min'] *= (resize_factor * self.mm_per_pixel)
        self.appearance_parameters['poly_rad_max'] *= (resize_factor * self.mm_per_pixel)
        #   Interior/exterior pixel extension of the blur annulus around the ellipses' edges
        self.appearance_parameters['blur_in_extension'] *= (resize_factor * self.mm_per_pixel)
        self.appearance_parameters['blur_out_extension'] *= (resize_factor * self.mm_per_pixel)
        # Adding the above-gotten information to the class metadata dictionary
        self.metadata_dict['#feedback_1_x'] = self.ellipse_dimensions['center_coordinates'][0]
        self.metadata_dict['#feedback_1_y'] = self.ellipse_dimensions['center_coordinates'][1]
        #   Using twice the semi-axes lengths in pixels (necessary for proper Zooniverse feedback on simulations)
        self.metadata_dict['#feedback_1_toleranceA'] = 2 * axes_lengths_pix[0]
        self.metadata_dict['#feedback_1_toleranceB'] = 2 * axes_lengths_pix[1]
        #   Converting the rotation to its counterclockwise value  (necessary for proper Zooniverse feedback on simulations)
        self.metadata_dict['#feedback_1_theta'] = 180 - angle
        self.metadata_dict['#major_to_minor_ratio'] = self.ellipse_dimensions['major_to_minor_ratio']
        self.metadata_dict['#appearance_parameters'] = self.appearance_parameters

    def dump(self):
        """
        Returns the class metadata dictionary in a form amenable to being written into CSVs and .xlsx files;
        checks whether all wanted and no unwanted metadata was given.
        """
        # Copying the class metadata dictionary, so as not to alter it
        dict_to_dump = self.metadata_dict.copy()
        # Converting the dictionary's dictionaries into strings
        dict_to_dump['#appearance_parameters'] = json.dumps(dict_to_dump['#appearance_parameters'])
        # Checking whether all metadata field in the class dictionary were filled and none were added
        verify_dict(dict_to_dump, 'simulation', simulation_fieldnames)
        return dict_to_dump


def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def print_status(subject_type, current_id, first_id, final_id, n_tabs=2):
    tabs = '\t' * n_tabs
    status = f'\r\t\t{subject_type.capitalize()} subject {current_id - first_id + 1} of {final_id - first_id + 1} created.'
    print(tabs + status, end='' if current_id != final_id else '\n')


class ProcessImages:
    """
    Performs all the necessary steps to create, document, and upload experiment and simulation subjects.
    """

    def __init__(self, download_now=False, upload_now=False, should_draw_scale_bars=False, should_clear_folders=False):
        self.download_now = download_now
        self.upload_now = upload_now
        self.should_draw_scale_bars = should_draw_scale_bars
        self.should_clear_folders = should_clear_folders
        if download_now is True or upload_now is True:
            # Initializing a class used to interact with Google Drive
            self.gd = GoogleDriveUtils()
        # Initializing...
        # ... Manifests
        self.experiment_manifest = ExcelUtils(experiment_manifest_path, experiment_fieldnames)
        self.simulation_manifest = ExcelUtils(simulation_manifest_path, simulation_fieldnames)
        self.processed_slabs_manifest = ExcelUtils(processed_slabs_manifest_path, processed_slabs_fieldnames)
        self.processed_folders_manifest = ExcelUtils(processed_folders_manifest_path, processed_folders_fieldnames)
        # ... Backup (CSV) manifests
        self.experiment_manifest_csv = CsvUtils(experiment_manifest_csv_path, experiment_fieldnames)
        self.simulation_manifest_csv = CsvUtils(simulation_manifest_csv_path, simulation_fieldnames)
        self.processed_slabs_manifest_csv = CsvUtils(processed_slabs_manifest_csv_path, processed_slabs_fieldnames)
        self.processed_folders_manifest_csv = CsvUtils(processed_folders_manifest_csv_path,
                                                       processed_folders_fieldnames)
        # ... Zooniverse CSV manifests
        self.experiment_csv = CsvUtils(experiment_csv_path, experiment_fieldnames)
        self.simulation_csv = CsvUtils(simulation_csv_path, simulation_fieldnames)
        # Getting a list of the IDs of already processed slabs, so that the area of slabs
        # coming from the same block are not counted in `examinable_area'
        self.already_processed_slab_ids = self.get_already_processed_slab_ids()
        # Initializing dictionaries to contain first and second folders, with key-value pairs:
        #   '(name)': (FirstFolder/SecondFolder instance)
        self.first_folders = {}
        self.second_folders = {}
        # Initializing dictionaries to contain experiment and simulation subjects; key-value pairs:
        #   '(subject ID)': (ExperimentSubject or SimulationSubject instance)
        self.experiment_subjects = {}
        self.simulation_subjects = {}

    def get_already_processed_slab_ids(self):
        """
        Returns a list of the warehouse-assigned IDs of slabs that have already been processed.
        """
        slab_dictionaries = self.processed_slabs_manifest_csv.read_rows(dict_reader=True)
        already_processed_slab_ids = []
        [already_processed_slab_ids.append(y) for d in slab_dictionaries
         if (y := d['slab_id']) not in already_processed_slab_ids]
        return already_processed_slab_ids

    def run(self):
        """
        Creates, documents, and uploads experiment and simulation images.
        """
        if self.should_clear_folders is True:
            self.clear_folders()
        if self.download_now is True:
            self.gd.download_from_staging_ground()
            self.gd.update_Name_ID_Manifest()
        self.initialize_folders()
        self.update_slab_manifest()
        self.create_experiment_subjects()
        self.create_simulation_subjects()
        self.update_folders_manifest()
        # TODO: uncomment below
        # self.upload_subjects()
        # self.upload_records()

    @staticmethod
    def clear_folders():
        """
        Clears (deletes) the contents of the folders used for image processing: the zeroth folder; the experiment and
        simulation subjects folders.
        """
        clear_folder(unprocessed_images_zeroth_folder)
        clear_folder(experiment_subjects_folder)
        clear_folder(simulation_subjects_folder)

    def initialize_folders(self):
        """
        Initializes FirstFolder instances for all 'first folders' and SecondFolder instances for 'second folders'
        whose images depict a slab originating from a block not already processed. Adds FirstFolder instances to
        self.first_folders and the 'first_folder' attribute of its SecondFolder's; adds SecondFolder instances to
        self.second_folders and the 'second_folders' attribute of its FirstFolder.
        """
        first_folder_names = get_subfolder_names(unprocessed_images_zeroth_folder)
        for first_folder_name in first_folder_names:
            self.first_folders[first_folder_name] = FirstFolder(first_folder_name)
            second_folder_names = get_subfolder_names(self.first_folders[first_folder_name].path)
            for second_folder_name in second_folder_names:
                parent_slab_id = second_folder_name.split('_')[0].split('-')[0]
                # Flag determining whether this the area of the images in this second folder can be counted towards
                # the total slab area examined
                tally_area = True
                if parent_slab_id.isnumeric() and parent_slab_id in self.already_processed_slab_ids:
                    # Ignoring the area of images depicting slabs cut from blocks already processed;
                    # the first condition  accounts for the fact that slab IDs may be unknown and given as 'u'
                    tally_area = False
                self.second_folders[second_folder_name] = \
                    self.first_folders[first_folder_name].second_folders[second_folder_name] = \
                    SecondFolder(second_folder_name, self.first_folders[first_folder_name], tally_area)

    def update_slab_manifest(self):
        """
        Updates the manifest tracking processed slabs' information using first and second folder names.
        """
        # Getting the starting processed-slab identification number
        starting_number = self.processed_slabs_manifest.get_first_empty_row() - 1
        slabs_metadata = []
        for first_folder in self.first_folders.values():
            for number, second_folder in enumerate(first_folder.second_folders.values(), start=starting_number):
                slabs_metadata.append({
                    'number': number,
                    'slab_id': second_folder.slab_id,
                    'granite_type': second_folder.granite_type,
                    'warehouse': first_folder.warehouse,
                    'location': first_folder.location,
                    'columns_or_rows': second_folder.cols_or_rows,
                    'number_columns_or_rows': second_folder.n_cols_or_rows,
                    'date_imaged': first_folder.date,
                    'images_taken': len(second_folder.unprocessed_images),
                    'image_dimensions': first_folder.uncropped_image_dimensions_in})
        if slabs_metadata:
            self.processed_slabs_manifest.write_rows(slabs_metadata, dict_writer=True)
            self.processed_slabs_manifest_csv.write_rows(slabs_metadata, dict_writer=True)

    def create_experiment_subjects(self):
        """
        Creates experiment subjects, adds ExperimentSubject instances to self.experiment_subjects, writes metadata
        to the Zooniverse manifest, running manifest and CSV copy.
        """
        # Getting the starting experiment identification number for the subjects in this batch
        global_experiment_id0 = self.experiment_manifest.get_first_empty_row() - 1  # accounting for fieldname row
        # Initializing a variable to track the starting experiment ID within each second folder
        second_folder_experiment_id0 = global_experiment_id0
        # Initializing a list of hold all experiment subjects' metadata (manifest rows)
        experiment_subjects_metadata = []
        # Iterating through first and second folders
        print('\n< EXPERIMENT SUBJECTS >')
        for first_folder in self.first_folders.values():
            print(f'{first_folder.name}...')  # printing status
            for second_folder in first_folder.second_folders.values():
                print(f'\t{second_folder.name}...')  # printing status
                # Getting the second folder's 'pre-experiment' images (cropped images if cropping was necessary,
                # ordinary images otherwise)
                if second_folder.cropping_necessary:
                    pre_experiment_images = second_folder.cropped_images
                else:
                    pre_experiment_images = second_folder.unprocessed_images
                # Getting the ID of the final experiment image to be made from this second folder
                second_folder_final_id = second_folder_experiment_id0 + len(pre_experiment_images) - 1
                # Assigning the first and last experiment ID to the second folder's experiment ID endpoints
                second_folder.experiment_id_endpoints = (second_folder_experiment_id0, second_folder_final_id)
                # Iterating through pre-experiment images
                for experiment_id, pre_experiment_image in enumerate(
                        pre_experiment_images, start=second_folder_experiment_id0):
                    # Appending an ExperimentSubject instance to the class-list
                    self.experiment_subjects[experiment_id] = ExperimentSubject(
                        experiment_id, pre_experiment_image, self.should_draw_scale_bars)
                    # Creating the experiment subject (see ExperimentSubject)
                    self.experiment_subjects[experiment_id].create()
                    # Appending this experiment subjects' metadata to the list initialized above
                    experiment_subjects_metadata.append(self.experiment_subjects[experiment_id].dump())
                    # Printing the updated number of experiment images thus far created
                    print_status('experiment', experiment_id, second_folder_experiment_id0, second_folder_final_id)
                # Updating 'second_folder_experiment_id0' such that it equals the starting experiment ID of the next
                # second folder; eg. if 2 images were created, the next starting ID is (previous starting ID) + 2 + 1
                second_folder_experiment_id0 = second_folder_final_id + 1
        # Writing experiment subjects' metadata into the Zooniverse manifest, running manifest and CSV copy
        self.experiment_csv.write_rows(experiment_subjects_metadata, dict_writer=True)
        self.experiment_manifest.write_rows(experiment_subjects_metadata, dict_writer=True)
        self.experiment_manifest_csv.write_rows(experiment_subjects_metadata, dict_writer=True)

    def create_simulation_subjects(self):
        """
        Creates simulation subjects, adds SimulationSubject instances to self.simulation_subjects, writes metadata
        to the Zooniverse manifest, running manifest and CSV copy.
        """
        # Getting the starting simulation identification number for the subjects in this batch
        global_simulation_id0 = self.simulation_manifest.get_first_empty_row() - 1  # accounting for fieldname row
        # Initializing a variable to track the starting simulation ID within each second folder
        second_folder_simulation_id0 = global_simulation_id0
        # Initializing a list of hold all simulation subjects' metadata (manifest rows)
        simulation_subjects_metadata = []
        # Iterating through first and second folders
        print('\n< SIMULATION SUBJECTS >')
        for first_folder in self.first_folders.values():
            print(f'{first_folder.name}...')  # printing status
            for second_folder in first_folder.second_folders.values():
                print(f'\t{second_folder.name}...')  # printing status
                # Sampling the experiment images from which simulation subjects will be made,
                # the number sampled per second folder being determined by a variable in 'subject_parameters'
                experiment_subjects = self.sample_experiment_subjects(second_folder)
                # Getting the ID of the final simulation image to be made from this second folder
                second_folder_final_id = second_folder_simulation_id0 + len(experiment_subjects) - 1
                # Assigning the first and last simulation ID to the second folder's simulation ID endpoints
                second_folder.simulation_id_endpoints = (second_folder_simulation_id0, second_folder_final_id)
                # Iterating through pre-simulation images
                for simulation_id, experiment_subject in enumerate(
                        experiment_subjects, start=second_folder_simulation_id0):
                    # Appending a SimulationSubject instance to the class-list
                    self.simulation_subjects[simulation_id] = SimulationSubject(simulation_id, experiment_subject)
                    # Creating the simulation subject (see SimulationSubject)
                    self.simulation_subjects[simulation_id].create()
                    # Appending this simulation subjects' metadata to the list initialized above
                    simulation_subjects_metadata.append(self.simulation_subjects[simulation_id].dump())
                    # Printing the updated number of experiment images thus far created
                    print_status('simulation', simulation_id, second_folder_simulation_id0, second_folder_final_id)
                # Updating 'second_folder_simulation_id0' such that it equals the starting simulation ID of the next
                # second folder; eg. if 2 images were created, the next starting ID is (previous starting ID) + 2 + 1
                second_folder_simulation_id0 = second_folder_final_id + 1
            # Writing simulation subjects' metadata into the Zooniverse manifest, running manifest and CSV copy
            self.simulation_csv.write_rows(simulation_subjects_metadata, dict_writer=True)
            self.simulation_manifest.write_rows(simulation_subjects_metadata, dict_writer=True)
            self.simulation_manifest_csv.write_rows(simulation_subjects_metadata, dict_writer=True)

    def sample_experiment_subjects(self, second_folder):
        """
        Returns a randomly sampled 'simulations_per_second_folder' ('subject_parameters' variable) number of experiment
        images made from each second folder to be used in the creation of simulation images.
        """
        # Getting a list of all ExperimentSubject and SecondFolder instances
        experiment_images = list(self.experiment_subjects.values())
        second_folders = list(self.second_folders.values())
        # Initializing a dictionary with key-value pairs:
        #   '(second folder name)': (list of ExperimentSubject's made from the images in this second folder)
        second_folder_images = dict((y.name, []) for y in second_folders)
        # Filling-in the above created dictionary
        [second_folder_images[e.second_folder.name].append(e) for e in experiment_images]
        # Sampling a 'simulations_per_second_folder' number of ExperimentSubject's from each second folder
        sampled_experiment_subjects = list(
            np.random.choice(second_folder_images[second_folder.name], simulations_per_second_folder))
        return sampled_experiment_subjects

    def update_folders_manifest(self):
        """
        Updates the manifest tracking processed folders and the IDs of subjects made from the images they contain.
        """
        folders_metadata = []
        for first_folder in self.first_folders.values():
            second_folders = first_folder.second_folders.values()
            second_folder_names = [s.name for s in second_folders]
            experiment_id_endpoints = [s.experiment_id_endpoints for s in second_folders]
            simulation_id_endpoints = [s.simulation_id_endpoints for s in second_folders]
            folders_metadata.append({
                'date_processed': date.today(),
                'first_folder': first_folder.name,
                'second_folders': second_folder_names,
                'experiment_id_endpoints': experiment_id_endpoints,
                'simulation_id_endpoints': simulation_id_endpoints})
        if folders_metadata:
            self.processed_folders_manifest.write_rows(folders_metadata, dict_writer=True)
            self.processed_folders_manifest_csv.write_rows(folders_metadata, dict_writer=True)

    def upload_subjects(self):
        # Uploading subjects to...
        # ... Zooniverse
        upload_subjects_to_zooniverse(experiment_csv_path, experiment_subject_set_id)
        upload_subjects_to_zooniverse(simulation_csv_path, simulation_subject_set_id)
        # ... Google Drive
        self.gd.upload_folder(experiment_subjects_folder, self.gd.experiment_folder_id, replace_existing=True)
        self.gd.upload_folder(simulation_subjects_folder, self.gd.simulation_folder_id, replace_existing=True)

    def upload_records(self):
        # Uploading to Google Drive...
        # ... Running manifests
        self.gd.upload_file(experiment_manifest_path, self.gd.manifests_folder_id, replace_existing=True)
        self.gd.upload_file(simulation_manifest_path, self.gd.manifests_folder_id, replace_existing=True)
        self.gd.upload_file(processed_slabs_manifest_path, self.gd.manifests_folder_id, replace_existing=True)
        self.gd.upload_file(processed_folders_manifest_path, self.gd.manifests_folder_id, replace_existing=True)
        self.gd.upload_file(name_id_manifest_path, self.gd.manifests_folder_id, replace_existing=True)
        # ... CSV copies
        self.gd.upload_file(experiment_manifest_csv_path, self.gd.manifests_csv_folder_id, replace_existing=True)
        self.gd.upload_file(simulation_manifest_csv_path, self.gd.manifests_csv_folder_id, replace_existing=True)
        self.gd.upload_file(processed_slabs_manifest_csv_path, self.gd.manifests_folder_id, replace_existing=True)
        self.gd.upload_file(processed_folders_manifest_csv_path, self.gd.manifests_folder_id, replace_existing=True)
        self.gd.upload_file(name_id_manifest_csv_path, self.gd.manifests_csv_folder_id, replace_existing=True)
        # Pushing all of the above to GitHub
        files_to_push = [experiment_manifest_path, simulation_manifest_path, processed_slabs_manifest_path,
                         processed_folders_manifest_path, name_id_manifest_path, experiment_manifest_csv_path,
                         simulation_manifest_csv_path, processed_slabs_manifest_csv_path,
                         processed_folders_manifest_csv_path, name_id_manifest_csv_path]
        push_files_to_GitHub(files_to_push, f"update records, {date.today()}")


if __name__ == '__main__':
    # TODO: delete all 'remove_file'
    from python.utils.file_utils import remove_file
    remove_file(processed_slabs_manifest_path)
    remove_file(processed_slabs_manifest_csv_path)
    remove_file(experiment_manifest_path)
    remove_file(experiment_manifest_csv_path)
    remove_file(simulation_manifest_path)
    remove_file(simulation_manifest_csv_path)
    remove_file(processed_folders_manifest_path)
    remove_file(processed_folders_manifest_csv_path)
    clear_folder(experiment_subjects_folder)
    clear_folder(simulation_subjects_folder)
    t = time.time()
    pi = ProcessImages(should_draw_scale_bars=False)
    pi.run()
    print(f'\nRuntime: {round(time.time() - t, 2)} seconds.')
