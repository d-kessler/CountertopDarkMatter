import os
import cv2
import numpy as np
from blend_modes import multiply

from python.utils.cv_utils import get_glare_area

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir(os.path.join(".."))


# ELLIPSE FUNCTIONS
"""
For the functions below,
    cx: ellipse center x-coordinate
    cy: ellipse center y-coordinate
    xdim: ellipse x-semi-axis length
    ydim: ellipse y-semi-axis length
    angle: clockwise rotation (clockwise angle wrt the x-axis) in radians
"""


def parametric_ellipse(cx, cy, xdim, ydim, angle, points=1000, num_sectors=None, dtype=float):
    """
    Returns arrays of x and y coordinates of the boarder pixels of an ellipse.
        points: number of points used in the parametrization
        num_sectors: number of ellipse sectors in which to vary "points"
                     as a function of average distance to ellipse center
        dtype: data type of the return arrays (eg. int, float)
    """
    if num_sectors is None:
        t = np.linspace(0, 2 * np.pi, points)
    else:
        sector_paramters = np.linspace(0, 2 * np.pi, num_sectors)
        sector_coordinates = eval_parametric_ellipse(cx, cy, xdim, ydim, angle, sector_paramters)
        dists_to_center = ((sector_coordinates[0] - cx) ** 2 + (sector_coordinates[1] - cy) ** 2) ** (1 / 2)
        avg_dists_to_center = (dists_to_center[:-1:] + dists_to_center[1::]) / 2
        avg_dist_to_center = np.sum(avg_dists_to_center) / len(avg_dists_to_center)
        sector_num_points = ((points / num_sectors) * (avg_dists_to_center / avg_dist_to_center)).astype(int)
        t = np.zeros(np.sum(sector_num_points))
        for i in range(len(sector_paramters) - 1):
            t[np.sum(sector_num_points[0:i]):np.sum(sector_num_points[0:i + 1])] = \
                np.linspace(sector_paramters[i], sector_paramters[i + 1], sector_num_points[i])
    boundary_x = (cx + xdim * np.cos(angle) * np.cos(t) - ydim * np.sin(angle) * np.sin(t)).astype(dtype)
    boundary_y = (cy + xdim * np.sin(angle) * np.cos(t) + ydim * np.cos(angle) * np.sin(t)).astype(dtype)
    return boundary_x, boundary_y


def eval_parametric_ellipse(cx, cy, xdim, ydim, angle, parameter, dtype=float):
    """ Evaluates the general parametric ellipse equation at "parameter", returns (x, y). """
    t = parameter
    x = (cx + xdim * np.cos(angle) * np.cos(t) - ydim * np.sin(angle) * np.sin(t)).astype(dtype)
    y = (cy + xdim * np.sin(angle) * np.cos(t) + ydim * np.cos(angle) * np.sin(t)).astype(dtype)
    return x, y


def ellipse_extrema(cx, cy, xdim, ydim, angle):
    """ Returns the pixel-coordinate extrema of the ellipse's boarder, (min_x, max_x, min_y, max_y). """
    boundary_x, boundary_y = parametric_ellipse(cx, cy, xdim, ydim, angle)
    min_x, max_x = np.ceil(boundary_x.min()).astype(int), np.ceil(boundary_x.max()).astype(int)
    min_y, max_y = np.ceil(boundary_y.min()).astype(int), np.ceil(boundary_y.max()).astype(int)
    return min_x, max_x, min_y, max_y


def ellipse_eq_lhs(x, y, cx, cy, xdim, ydim, angle):
    """
    Returns the value of the left hand side of the general ellipse equation,
    (https://math.stackexchange.com/questions/426150).
    A value <1 implies that the point (x,y) falls inside of the specified ellipse.
        x: point x-coordinate
        y: point y-coordinate
    """
    return (((x - cx) * np.cos(angle) + (y - cy) * np.sin(angle)) / xdim) ** 2 + \
           (((x - cx) * np.sin(angle) - (y - cy) * np.cos(angle)) / ydim) ** 2


def get_ellipse_pixels(image_h, image_w, center_coords, axes_lengths, angle):
    """Returns a list of pixels contained within the given ellipse."""
    white_img = 255 * np.ones((image_h, image_w), dtype=np.uint8)
    ellipse_img = cv2.ellipse(white_img, center_coords, axes_lengths, angle, 0, 360, 0, -1)
    ellipse_pixel_rows, ellipse_pixel_cols = np.where(ellipse_img == 0)
    ellipse_pixels = list(zip(ellipse_pixel_rows, ellipse_pixel_cols))
    return ellipse_pixels


def get_bounded_ellipse_image(ellipse_image):
    """
    Returns the smallest possible section of "ellipse_image" containing the whole of the ellipse.
        ellipse_image: black (0) ellipse on a white (255) background
    """
    ellipse_image_min_x, ellipse_image_min_y = [a.min() for a in np.where(ellipse_image == 0)]
    ellipse_image_max_x, ellipse_image_max_y = [a.max() for a in np.where(ellipse_image == 0)]
    return ellipse_image[ellipse_image_min_x: ellipse_image_max_x,
                         ellipse_image_min_y: ellipse_image_max_y]


def ellipse_arc_length(xdim, ydim, angle, t_start, t_end):
    import scipy.integrate as integ
    def x_prime(t, xdim, ydim, angle):
        return - xdim * np.cos(angle) * np.sin(t) - ydim * np.sin(angle) * np.cos(t)
    def y_prime(t, xdim, ydim, angle):
        return - xdim * np.sin(angle) * np.sin(t) + ydim * np.cos(angle) * np.sin(t)
    def arc_length_integrand(t, xdim, ydim, angle):
        params = (t, xdim, ydim, angle)
        return np.sqrt(x_prime(*params)**2 + y_prime(*params)**2)
    arc_length = integ.quad(arc_length_integrand, t_start, t_end, args=(xdim, ydim, angle))
    return arc_length


def draw_dashed_ellipse(image, cx, cy, xdim, ydim, angle, color, thickness,
                        border_gaps_angular_extent, border_segments_angular_extent):
    # border_gaps_angular_extent = 0 <=> continuous line
    if border_gaps_angular_extent == 0:
        return cv2.ellipse(image, (cx, cy), (xdim, ydim), angle, 0, 360, color, thickness)
    for i in range(360):
        if border_gaps_angular_extent == 0:
            draw_section_here = True
        elif i % border_gaps_angular_extent == 0:
            draw_section_here = True
        else:
            draw_section_here = False
        if draw_section_here is False:
            continue
        start_angle = i
        end_angle = i + border_segments_angular_extent
        ellipse_img = cv2.ellipse(image, (cx, cy), (xdim, ydim), angle,
                                  start_angle, end_angle, color, thickness)
    return ellipse_img


def resize_ellipse_dimensions(center_coordinates, axes_lengths, angle, resize_factor):
    """
    Adjust the ellipse's dimensions according to the factor by which its image's pixel dimensions were resized.
        center_coordinates: the x, y center (pixel) coordinates of the ellipse
        axes_lengths: the x, y axes lengths (pixels) of the ellipse
        angle: the clockwise rotation (degrees) of the ellipse
        resize_factor: the factor by which the image's pixel dimensions were resized
    """
    # Center coordinates measure the length (in pixels) between the center of the ellipse and the top-left corner
    # of the image; since image dimensions are scaled by resize_factor, so too are these lengths
    center_coordinates = tuple([c * resize_factor for c in center_coordinates])
    # Axes lengths are the hypotenuses' of right triangles, each of whose legs are scaled by resize_factor, and are
    # therefore scaled by resize_factor
    axes_lengths = tuple([a * resize_factor for a in axes_lengths])
    #   The rotation of the ellipse is unaffected when its axes lengths are scaled by a constant factor
    angle = angle
    return center_coordinates, axes_lengths, angle


# MISC. FUNCTIONS

def transparent_image(bgra_image):
    """
    Converts the white background of a BGRA image to have an alpha of 0 (wholly transparent),
    returns the transparent image.
        bgra_image: cv2 image array with BGRA color format and white background
    """
    white_mask = (cv2.cvtColor(bgra_image, cv2.COLOR_BGRA2GRAY) == 255)
    bgra_image[white_mask, -1] = 0
    return bgra_image


def to_bgra(image):
    """Converts an image to the BGRA color scheme if it doesn't use it already."""
    if image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    return image


def adjust_gamma(image, gamma=1.0):
    """
    Adjust image luminance.
        image: cv2 image array
        gamma: parameter determining image luminance adjustment
    """
    adjusted_image = np.array([
        ((i / 255.0) ** (1.0 / gamma)) * 255
        for i in np.arange(0, 256)])
    return cv2.LUT(image.astype(np.uint8), adjusted_image.astype(np.uint8))


def polygon(number_of_sides, radius, rotation, cx, cy):
    """
    Returns lists of the x and y pixel coordinates of the vertices of a regular polygon.
        number_of_sides: the polygon's number of sides
        radius: the polygon's radius
        rotation: the polygon's rotation
        cx: the polygon's center x-coordinate
        cy: the polygon's center y-coordinate
    """
    theta = (2 * np.pi) / number_of_sides
    x = [cx + np.cos(rotation) * radius * np.cos(i * theta) + np.sin(rotation) * radius * np.sin(i * theta) for i in
         range(number_of_sides)]
    y = [cy - np.sin(rotation) * radius * np.cos(i * theta) + np.cos(rotation) * radius * np.sin(i * theta) for i in
         range(number_of_sides)]
    return x, y


def get_embedded_indices(exterior_image, interior_image, centered_about=None):
    """
    Gets indices of "interior_image" about "centered_about" in "exterior_image";
    centered_about = None <=> centered_about = center of exterior_image.
    """
    if centered_about is None:
        h_diff, w_diff = list(np.array(exterior_image.shape) - np.array(interior_image.shape))[0:2]
        embedded_indices = np.index_exp[
                           np.floor(h_diff / 2).astype(int): - np.ceil(h_diff / 2).astype(int),
                           np.floor(w_diff / 2).astype(int): - np.ceil(w_diff / 2).astype(int)]
        if len(exterior_image.shape) == 3:
            embedded_indices = tuple(list(embedded_indices) + [slice(None, None, None)])
    else:
        interior_h, interior_w = interior_image.shape[0:2]
        embedded_indices = np.index_exp[
                           centered_about[1] - np.floor(interior_h / 2).astype(int):centered_about[1] + np.ceil(
                               interior_h / 2).astype(int),
                           centered_about[0] - np.floor(interior_w / 2).astype(int):centered_about[0] + np.ceil(
                               interior_w / 2).astype(int)]
        if len(exterior_image.shape) == 3:
            embedded_indices = tuple(list(embedded_indices) + [slice(None, None, None)])
    return embedded_indices


class SimUtils:
    # Number of regions in which the number of polygons to-be-drawn is independently
    # calculated using the region's average distance to the ellipse center
    num_sectors = 30
    # Coefficient in the equation: (total number of polygons) = C * (semi-major axis length)
    max_axis_to_polygons_coefficient = 20
    # Opacity of the multiplied ellipse with respect to the underlying granite
    opacity = 0.85  # Closer to 0 <=> More transparent
    # "Unmask-sharpening" parameters used to sharpen the ellipse image
    blur_radius = 1.5  # Standard deviation of Gaussian blur
    unsharp_factor = 7  # Larger <=> More sharp
    # Gamma (luminance) and alpha (contrast) adjustment parameters in the
    # order that they will be applied
    gamma_adj = 1.1  # > 1 <=> Shadows become darker
    alpha_adj = 1.85  # Larger <=> Greater contrast
    gamma_re_adj = 0.8  # < 1 <=> Shadows become lighter
    # The dimension of the kernel used for blurring
    blur_kernel_dim = 3  # Larger <=> More blurry

    def __init__(self, granite_image_path, destination_image_path, mm_per_pixel, minor_axis_min=1, minor_axis_max=6,
                 minor_axis_step=1, major_axis_selection="distribution", major_axis_max=(2*25.4),
                 poly_rad_min=0.1, poly_rad_max=0.3, poly_sides_min=3, poly_sides_max=8,
                 circle=False, center_coordinates=None, axes_lengths=None, angle=None):
        """
        granite_image_path: file path to the granite image onto which the simulation is to be drawn
        destination_image_path: file path to which the simulation image is to be saved
        mm_per_pixel: the millimeter per pixel ratio of the granite image
        minor_axis_min: the minimum semi-minor axis length in millimeters
        minor_axis_max: the maximum semi-minor axis length in millimeters
        minor_axis_step: step size in the grid of options for semi-minor axis length
        major_axis_selection: "distribution" to draw a minor-to-major axis ratio from the expected
                              uniform distribution; "random" to select from the semi-minor axis options
        major_axis_max: maximum semi-major axis length in millimeters
        poly_rad_min: minimum radius of the regular polygons drawn around the simulation's edge in millimeters
        poly_rad_max: maximum radius of the regular polygons drawn around the simulation's edge in millimeters
            Note: the main determinant of edge roughness is the difference between min/max polygon radii
        poly_sides_min: minimum number of sides of the regular polygons drawn around the simulation's edge
        poly_sides_max: maximum number of sides of the regular polygons drawn around the simulation's edge
        circle: True for the simulation to be circled in green
        center_coordinates: a tuple of the simulation's center pixel-coordinates
        axes_lengths: a tuple of the simulation's semi-minor and -major axis lengths in pixels, as measured with
                      respect to the x- and y-axes when the simulation is not rotated
        angle: clockwise rotation of the simulation in degrees
        """
        self.granite_image_path = granite_image_path
        self.granite_img = cv2.imread(granite_image_path)
        self.destination_image_path = destination_image_path
        self.mm_per_pixel = mm_per_pixel
        self.minor_axis_options = np.arange(minor_axis_min, minor_axis_max + minor_axis_step, minor_axis_step)
        self.major_axis_selection = major_axis_selection
        self.major_axis_max = major_axis_max
        self.poly_rad_min = poly_rad_min / self.mm_per_pixel
        self.poly_rad_max = poly_rad_max / self.mm_per_pixel
        self.poly_sides_min = poly_sides_min
        self.poly_sides_max = poly_sides_max
        self.circle = circle
        # Interior/exterior pixel extension of the blur annulus around the ellipses' edges
        self.blur_in_extension = self.poly_rad_max
        self.blur_out_extension = self.poly_rad_max * 2
        if [center_coordinates, axes_lengths, angle] != [None] * 3:
            self.center_coordinates, self.axes_lengths, self.angle = center_coordinates, axes_lengths, angle
        else:
            self.center_coordinates, self.axes_lengths, self.angle = self.get_ellipse_params()
        self.tune_ellipse_params()

    def get_ellipse_params(self):
        """Returns pixel center_coordinates (x, y), axes_lengths (xdim, ydim), and angle (0 - 180 degrees)."""
        # Randomly selecting center coordinates that fall within the granite image
        center_coordinates = \
            tuple((np.array(self.granite_img.shape[0:2][::-1]) * np.random.random(2)).astype(int))
        minor_axis_mm = np.random.choice(self.minor_axis_options)
        # If specified, selecting a major axis according to the expected distribution
        if self.major_axis_selection == "distribution":
            # Ensuring that the selected major axis is not larger than the image dimensions
            # (would cause bugs / visual glitches)
            acceptable_major_axis = False
            while not acceptable_major_axis:
                # Randomly selecting a minor-to-major axis ratio between zero and one
                # (m/M = cos(theta) and theta is uniformly distributed wrt cos(theta))
                minor_to_major_ratio = np.random.random()
                major_axis_mm = minor_axis_mm / minor_to_major_ratio
                acceptable_major_axis = (major_axis_mm < self.major_axis_max)
        # Otherwise, choosing a major axis from the given choice of minor axes
        else:
            major_axis_mm = np.random.choice(self.minor_axis_options)
        # Converting axes lengths from millimeters to pixels
        # Remark: by default the major axis is the x-axis dimension;
        # this is unimportant due to the random choice of rotation
        axes_lengths_mm = [major_axis_mm, minor_axis_mm]
        axes_lengths_pix = tuple([int(a / self.mm_per_pixel) for a in axes_lengths_mm])
        # Getting a random angle of rotation wrt the negative x-axis in degrees
        angle = int(np.random.random() * 180)
        return center_coordinates, axes_lengths_pix, angle

    def tune_ellipse_params(self):
        """
        Prevents any portion of the selected ellipse to extend past the edges of the image
        (which would cause bugs / visual glitches) or overlap with glared portion of the slab.
        Returns pixel center_coordinates (x, y), axes_lengths (xdim, ydim),  and angle (0 - 180 degrees).
        """
        glare_pixels = get_glare_area(self.granite_image_path, self.mm_per_pixel, get_pixels=True)[1]
        attempts, max_attempts = 0, 50
        while self.get_overextended() or self.get_glare_overlap(glare_pixels):
            self.center_coordinates = \
                tuple((np.array(self.granite_img.shape[0:2][::-1]) * np.random.random(2)).astype(int))
            if (attempts := attempts + 1) > max_attempts:
                self.get_new_ellipse_params()
                attempts = 0

    def get_overextended(self):
        """Returns True if the class-wide ellipse extends past the edge of the granite image."""
        min_x, max_x, min_y, max_y = \
            ellipse_extrema(*self.center_coordinates, *self.axes_lengths, np.deg2rad(self.angle))
        left = (min_x < 0)
        right = (max_x > self.granite_img.shape[1])
        top = (min_y < 0)
        bottom = (max_y > self.granite_img.shape[0])
        if left or top or right or bottom:
            return True
        return False

    def get_glare_overlap(self, glare_pixels):
        """Returns true if the class-wide ellipse overlaps with glared portions of granite."""
        ellipse_pixels = get_ellipse_pixels(*self.granite_img.shape[0:2], self.center_coordinates,
                                            self.axes_lengths, self.angle)
        if list(set(ellipse_pixels) & set(glare_pixels)):
            return True
        return False

    def get_new_ellipse_params(self):
        """Selects a new set of class-wide ellipse parameters."""
        self.center_coordinates, self.axes_lengths, self.angle = self.get_ellipse_params()

    def draw_sim(self):
        """
        Draws a simulation ellipse of the given dimensions onto the given granite image, saving to the given file path.
        """
        ellipse_img_sect_bgra, img_sect_indices, ellipse_mask = self.create_ellipse_image()
        multiplied_img_sect = self.multiply_ellipse(ellipse_img_sect_bgra, img_sect_indices, ellipse_mask)
        sharpened_img_sect = self.sharpen_ellipse_image(multiplied_img_sect)
        gamma_adj_img_sect = adjust_gamma(sharpened_img_sect, gamma=self.gamma_adj)
        gamma_adj_img_sect = transparent_image(gamma_adj_img_sect)
        contrast_adj_img_sect = cv2.convertScaleAbs(gamma_adj_img_sect, alpha=self.alpha_adj)  # Adjust image contrast.
        contrast_adj_img_sect = to_bgra(contrast_adj_img_sect)
        gamma_re_adj_img_sect = adjust_gamma(contrast_adj_img_sect, gamma=self.gamma_re_adj)
        cutout_ellipse_img_sect = self.cutout_ellipse(gamma_re_adj_img_sect)
        to_paste_img = cutout_ellipse_img_sect.astype("float32")
        pasted_img = self.paste_ellipse_image(to_paste_img)
        blurred_edges_img = self.blur_ellipse_edges(pasted_img)
        final_img = blurred_edges_img
        if self.circle is True:
            final_img = cv2.circle(final_img, self.center_coordinates, 150, (0, 255, 0), 2)
        cv2.imwrite(self.destination_image_path, final_img)

    def create_ellipse_image(self):
        """
        Draws onto a white image an ellipse with a jagged edge (the result of drawing random regular-polygons).
        """
        # Creating a blank image of the same shape as granite_img
        white_img = 255 * np.ones(self.granite_img.shape, np.uint8)
        # Drawing an ellipse of the specified dimensions onto the blank image
        start_angle, end_angle, color, thickness = 0, 360, (0, 0, 0), -1
        ellipse_img = cv2.ellipse(white_img, self.center_coordinates, self.axes_lengths, self.angle,
                                  start_angle, end_angle, color, thickness)
        # Getting a list of the ellipse's boarder's x- and y-coordinates
        ell_x, ell_y = parametric_ellipse(*self.center_coordinates, *self.axes_lengths, np.deg2rad(self.angle),
                                          points=max(list(self.axes_lengths))*self.max_axis_to_polygons_coefficient,
                                          num_sectors=self.num_sectors, dtype=int)
        # Initializing a random number generator
        rng = np.random.default_rng()
        # Each ellipse boarder pixel, getting random input for whether a polygon should be drawn
        draw_here = rng.integers(low=0, high=2, size=len(ell_x))
        # Iterating through ellipse boarder pixels
        ell_pts = list(zip(ell_x, ell_y))
        for i in range(len(ell_pts)):
            # If not drawing a polygon, continue to the next pixel
            if draw_here[i] == 0:
                continue
            # Getting random input for the polygon's number of sides
            number_of_sides = rng.integers(low=self.poly_sides_min, high=self.poly_sides_max + 1)  # inclusive of min/max
            # Getting random input for the polygon's radius
            try:
                radius = rng.integers(low=self.poly_rad_min, high=self.poly_rad_max)
            except ValueError:
                # Ensuring that the min and max radius differ by at a least a pixel
                radius = rng.integers(low=self.poly_rad_min, high=self.poly_rad_max + 1)
            # Getting random input for the polygon's rotation
            rotation = rng.uniform() * (2 * np.pi)
            # Getting a list of the coordinates of the polygon's vertices
            poly_x, poly_y = polygon(number_of_sides, radius, rotation, *ell_pts[i])
            poly_pts = np.array(list(zip(poly_x, poly_y)), dtype=np.int32)
            # Adding the filled-in polygon to the ellipse edge
            ellipse_img = cv2.fillPoly(ellipse_img, [poly_pts], color=color)
        # Getting the ellipse image's dimensions
        ell_img_h, ell_img_w = ellipse_img.shape[0:2]
        # Getting numpy array indices for the space occupied by the ellipse within the ellipse image
        img_sect_indices = np.index_exp[
            int(max(0, ell_y.min() - self.poly_rad_max)): int(min(ell_img_h, ell_y.max() + self.poly_rad_max)),
            int(max(0, ell_x.min() - self.poly_rad_max)): int(min(ell_img_w, ell_x.max() + self.poly_rad_max)), :]
        # Cropping the space occupied by the ellipse itself within the ellipse image
        ellipse_img_sect = ellipse_img[img_sect_indices].copy()
        # Converting the cropped section to BGRA and gray
        ellipse_img_sect_bgra = cv2.cvtColor(ellipse_img_sect, cv2.COLOR_BGR2BGRA)
        ellipse_img_sect_gray = cv2.cvtColor(ellipse_img_sect, cv2.COLOR_BGR2GRAY)
        # Getting a mask of all pixels in the ellipse image not belonging to the ellipse itself
        white_mask = (ellipse_img_sect_gray == 255)
        # Making all such pixels to be transparent
        ellipse_img_sect_bgra[white_mask, -1] = 0
        # Getting a mask of all ellipse pixels within the ellipse image
        ellipse_mask = (ellipse_img_sect_gray != 255)
        return ellipse_img_sect_bgra, img_sect_indices, ellipse_mask

    def multiply_ellipse(self, ellipse_img_sect_bgra, img_sect_indices, ellipse_mask):
        """
        Applies "multiply" to the result of "create_ellipse_image," such that
        the ellipse picks up the granite's granular texture.
        """
        # Adding an alpha layer to the granite image (if necessary)
        self.granite_img = to_bgra(self.granite_img)
        # Getting the granite image's original dtype
        granite_img_dtype = self.granite_img.dtype
        # Cropping the section of the granite image that is occupied by the ellipse
        granite_img_sect = self.granite_img[img_sect_indices].copy()
        # Converting the images' dtypes to be amenable with the 'multiply' function
        ellipse_img_sect_bgra = ellipse_img_sect_bgra.astype(np.float)
        granite_img_sect = granite_img_sect.astype(np.float)
        # Applying 'multiply' to the cropped granite image section
        multiplied_img_sect = multiply(granite_img_sect, ellipse_img_sect_bgra, self.opacity)
        # Reverting the multiplied image's dtype prior
        multiplied_img_sect = multiplied_img_sect.astype(granite_img_dtype)
        # Pasting the multiplied ellipse onto a white background
        white_img = 255 * np.ones(multiplied_img_sect.shape, dtype=np.uint8)
        white_img[ellipse_mask] = 0
        multiplied_img_sect = np.where(white_img == 0, multiplied_img_sect, white_img)
        return multiplied_img_sect

    def sharpen_ellipse_image(self, ellipse_img_sect):
        """
        Applies "unsharp masking."
        """
        blurred_ellipse_img_sect = cv2.GaussianBlur(ellipse_img_sect, (0, 0), self.blur_radius)
        sharpened_img = cv2.addWeighted(ellipse_img_sect, 1 + self.unsharp_factor,
                                        blurred_ellipse_img_sect, - self.unsharp_factor, 0)
        return sharpened_img

    def cutout_ellipse(self, ellipse_img_sect):
        """
        Resizes the polygon-edged ellipse to the size of the ordinary, smooth-edged ellipse and cuts-out
        the dark edge that forms around the ellipse as a result of the image manipulations performed.
        """
        # Getting the necessary color conversion
        if ellipse_img_sect.shape[2] == 3:
            gray_cvt = cv2.COLOR_BGR2GRAY
        elif ellipse_img_sect.shape[2] == 4:
            gray_cvt = cv2.COLOR_BGRA2GRAY
        # Getting a gray copy of the original (ellipse) image
        gray_img = cv2.cvtColor(ellipse_img_sect, gray_cvt)
        # Setting all ellipse pixels to pure black
        gray_img[(gray_img != 255)] = 0
        # Getting the image cropped about the corresponding the perfect ellipse (without polygons)
        white_img = 255 * np.ones(self.granite_img.shape[0:2], dtype=np.uint8)
        white_img_center = tuple([int(d / 2) for d in white_img.shape][0:2][::-1])
        start_angle, end_angle, color, thickness = 0, 360, 0, -1
        perfect_ellipse = cv2.ellipse(white_img, white_img_center, self.axes_lengths, self.angle,
                                      start_angle, end_angle, color, thickness)
        perfect_ellipse = get_bounded_ellipse_image(perfect_ellipse)
        # Resizing the (polygon-edged) ellipse image to the size of the perfect ellipse image
        resized_gray_img = cv2.resize(gray_img, perfect_ellipse.shape[::-1])
        # Getting indices corresponding to the rectangular area that the (centered) portion
        # of the resized image would occupy within the original image
        resized_gray_indices = get_embedded_indices(gray_img, resized_gray_img)
        # Pasting the resized image onto a blank image having the same dimensions as the original image
        rg_background_img = 255 * np.ones_like(gray_img)
        rg_background_img[resized_gray_indices] = resized_gray_img
        # Getting a mask of all ellipse pixels in the above created background image
        resized_ellipse_mask = (rg_background_img != 255)
        # Creating another blank image onto which the cutout ellipse will be pasted
        cutout_ellipse_img_sect = 255 * np.ones(ellipse_img_sect.shape)
        # Pasting the cutout ellipse
        cutout_ellipse_img_sect[resized_ellipse_mask] = ellipse_img_sect[resized_ellipse_mask]
        return cutout_ellipse_img_sect

    def paste_ellipse_image(self, ellipse_img_sect_bgra):
        """
        Pastes ellipse image (with transparent background) onto the granite image for which it was intended.
        """
        # Converting the granite image to RGBA (if necessary)
        self.granite_img = to_bgra(self.granite_img)
        # Making the background of the ellipse image transparent
        ellipse_img_sect_bgra = transparent_image(ellipse_img_sect_bgra)
        # Getting the indices of the ellipse image with respect to the granite image
        img_sect_indices = get_embedded_indices(self.granite_img, ellipse_img_sect_bgra,
                                                centered_about=self.center_coordinates)
        # Pasting the ellipse onto the granite image
        pasted_img = self.granite_img.copy()
        pasted_img_sect = pasted_img[img_sect_indices]
        if ellipse_img_sect_bgra.shape != pasted_img_sect.shape:
            p_h, p_w = pasted_img_sect.shape[0:2]
            ellipse_img_sect_bgra = ellipse_img_sect_bgra[:p_h, :p_w, :]
        # Ensuring consistent transparency
        ellipse_img_sect_alpha = ellipse_img_sect_bgra[:, :, 3] / 255.0
        pasted_img_sect_alpha = 1.0 - ellipse_img_sect_alpha
        for i in range(3):
            pasted_img_sect[:, :, i] = \
                (ellipse_img_sect_alpha * ellipse_img_sect_bgra[:, :, i]
                 + pasted_img_sect_alpha * pasted_img_sect[:, :, i])
        pasted_img[img_sect_indices] = pasted_img_sect
        return pasted_img

    def blur_ellipse_edges(self, pasted_img):
        """
        Applies Gaussian blur to smooth the pixelated edges of the ellipse that has been pasted onto the granite image.
        """
        # Converting the pasted image to BGR (if necessary)
        if pasted_img.shape[2] == 4:
            pasted_img = cv2.cvtColor(pasted_img, cv2.COLOR_BGRA2BGR)
        # Getting the lower and upper bounds (ellipses) for the blur
        outside_axes_lengths = tuple([int(a + self.blur_out_extension) for a in self.axes_lengths])
        inside_axes_lengths = tuple([max(1, int(a - self.blur_in_extension)) for a in self.axes_lengths])
        # Getting a mask corresponding to the annular region that will appear to blurred on the final image
        to_blur_mask = np.zeros_like(pasted_img, dtype=np.uint8)
        to_blur_mask = cv2.ellipse(to_blur_mask, self.center_coordinates, outside_axes_lengths, self.angle, 0, 360,
                                   (255, 255, 255), -1)  # Setting the exterior of the annular region to white
        to_blur_mask = cv2.ellipse(to_blur_mask, self.center_coordinates, inside_axes_lengths, self.angle, 0, 360,
                                   (0, 0, 0), -1)  # setting the interior of the annular region to black
        # Getting the blur kernel
        blur_kernel = tuple([self.blur_kernel_dim] * 2)
        # Blurring the pasted image in full
        blurred_img = cv2.GaussianBlur(pasted_img, blur_kernel, 0)
        # Replacing the masked portion of the pasted image with the blurred image,
        # such that only the edges of the ellipse appear to be blurred
        blurred_edges_img = np.where(to_blur_mask == np.array([255, 255, 255]), blurred_img, pasted_img)
        return blurred_edges_img
