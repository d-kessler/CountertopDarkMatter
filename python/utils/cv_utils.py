import os
import cv2
import statistics
import numpy as np
from imutils import perspective, contours, grab_contours

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir(os.path.join(".."))


def contour_area(contour):
    x = contour.vertices[:, 0]
    y = contour.vertices[:, 1]
    area = 0.5 * np.sum(y[:-1] * np.diff(x) - x[:-1] * np.diff(y))
    return np.abs(area)


def midpoint(ptA, ptB):
    return (ptA[0] + ptB[0]) * 0.5, (ptA[1] + ptB[1]) * 0.5


def canny_thresholds(img, sigma=0.33):
    # Compute the median of the single channel pixel intensities
    v = np.median(img)
    # Apply automatic Canny edge detection using the computed median
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    return lower, upper


def get_contours(prepared_cv2_img, cutoff_avg_dim):
    """
    Returns a list of the image's contours, their bounding-box dimensions (height, width), and total area (sq. pix).
        prepared_cv2_img = image prepared for contour detection (eg. converted to gray-scale, blurred, and/or thresholded)
        cutoff_avg_dim = the average bounding-box dimension below which contours are ignored
    """
    # Detecting contours
    lower_canny, upper_canny = canny_thresholds(prepared_cv2_img)
    edges_img = cv2.Canny(prepared_cv2_img, lower_canny, upper_canny)
    # Dilating to ensure that contour paths are continuous
    dil_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    dil_edges_img = cv2.dilate(edges_img, dil_kernel)
    # Getting, sorting a list of contours
    contours_list = cv2.findContours(dil_edges_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours_list = grab_contours(contours_list)
    if contours_list:
        (contours_list, _) = contours.sort_contours(contours_list)
    # Initializing lists
    wanted_contours_list = []
    contour_dims = []
    contour_areas = []
    for cont in contours_list:
        #  Creating bounding box
        box = cv2.minAreaRect(cont)
        box = cv2.boxPoints(box)
        box = np.array(box, dtype='int')
        box = perspective.order_points(box)
        # Getting box vertex coordinates
        (top_left, top_right, bot_right, bot_left) = box
        # Getting box side midpoints
        (top_mid_x, top_mid_y) = midpoint(top_left, top_right)
        (bot_mid_x, bot_mid_y) = midpoint(bot_left, bot_right)
        (left_mid_x, left_mid_y) = midpoint(top_left, bot_left)
        (right_mid_x, right_mid_y) = midpoint(top_right, bot_right)
        # Measuring the semi-major and semi-minor axes of the box in pixels
        pix_height = np.linalg.norm(np.array([top_mid_x, top_mid_y]) - np.array([bot_mid_x, bot_mid_y]))
        pix_width = np.linalg.norm(np.array([left_mid_x, left_mid_y]) - np.array([right_mid_x, right_mid_y]))
        # Getting the contour's average dimension (average of height/width)
        contour_avg_dim = (pix_height + pix_width) / 2
        # Ignoring contours that have an average dimension less than the specified cutoff
        if contour_avg_dim < cutoff_avg_dim:
            continue
        wanted_contours_list.append(cont)
        contour_dims.append((pix_height, pix_width))
        contour_areas.append(cv2.contourArea(cont))
    # Finding the total contour area in square pixels
    total_contour_area = sum(contour_areas)
    return wanted_contours_list, contour_dims, total_contour_area


def get_glare_area(image_path, mm_per_pixel, get_pixels=False):
    """
    Returns the total glare area in square millimeters and a list of the coordinates of all pixels in which glare was found.
    """
    cv2_img = cv2.imread(image_path)
    # Setting lower and upper color limits for thresholding
    lower = (240, 240, 240)
    upper = (255, 255, 255)
    # Getting pixels between lower and upper color limits (those corresponding to glare areas)
    mask = cv2.inRange(cv2_img, lower, upper)
    # Blurring to smooth edges
    mask = cv2.blur(mask, (10, 10))
    # Getting a list of the glare patches' edges/contours, dimensions and the total glare area
    glare_contours, glare_dims, total_glare_area = get_contours(mask, 2.5 / mm_per_pixel)
    # Converting the total glare area from square pixels to square millimeters
    total_glare_area_mmSq = round(total_glare_area * (mm_per_pixel ** 2), 5)
    if get_pixels is True:
        # Isolating glare areas on a blank (black) image to get a list of glare pixels
        blank_img = np.zeros(cv2_img.shape, np.uint8)
        isolated_glare_img = cv2.drawContours(blank_img, glare_contours, contourIdx=-1, color=(255, 255, 255),
                                              thickness=cv2.FILLED)
        glare_rows, glare_cols, _ = np.where(isolated_glare_img != 0)
        glare_pixels = list(zip(glare_rows, glare_cols))
        return total_glare_area_mmSq, glare_pixels
    return total_glare_area_mmSq


def get_grain_stats(image_path, mm_per_pixel):
    """
    Picks out the dark colored grains of the granite (those grains whose color is < 70 in gray-scale),
    returns the 'grain density' (area of these grains  / area of the image) and the 'grain statistics':
        the number of grains
        the average of mean bounding-box height and mean bound-box width
        the median of the above
        the 25th %ile of the above
        the 75th %ile of the above
    """
    # Configuring the original image, getting its 'millimeter per pixel' scale
    cv2_img = cv2.imread(image_path)
    # Converting to grayscale
    gray_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2GRAY)
    # Blurring grayscale image
    blurred_img = cv2.GaussianBlur(gray_img, (9, 9), 0)
    # Segmenting blurred image to separate dark grains from background
    segmentation_thresh = 70
    thresh_img = cv2.threshold(blurred_img, segmentation_thresh, 255, cv2.THRESH_BINARY)[1]
    # Opening (erosion followed by dilation) segmented image to close holes within grains
    kernel = np.ones((9, 9), np.uint8)
    opened_img = cv2.morphologyEx(thresh_img, cv2.MORPH_OPEN, kernel, 5)
    # Getting a list of the grains' edges/contours, dimensions, and total area
    grain_contours_list, grain_dims, total_grain_area = get_contours(opened_img, 0.015 / mm_per_pixel)
    # Converting the grain dimensions from pixels to millimeters
    grain_dims_mm = [(x * mm_per_pixel, y * mm_per_pixel) for x, y in grain_dims]
    # Finding the total image area in square pixels
    h, w = cv2.imread(image_path).shape[0:2]
    image_area_pix = h * w
    # Getting the image's grain density (area of grains / area of image)
    grain_density = total_grain_area / image_area_pix
    # Getting statistics on the image's grains
    h = [g[0] for g in grain_dims_mm]
    w = [g[1] for g in grain_dims_mm]
    grain_stats = {
        'number': len(grain_dims_mm),
        'mean_size': round(statistics.mean([statistics.mean(h), statistics.mean(w)]), 3),
        'median_size': round(statistics.median([statistics.median(h), statistics.median(w)]), 3),
        '25th_size': round(statistics.mean([np.percentile(h, 25), np.percentile(w, 25)]), 3),
        '27th_size': round(statistics.mean([np.percentile(h, 75), np.percentile(w, 75)]), 3)}
    return round(grain_density, 5), grain_stats
