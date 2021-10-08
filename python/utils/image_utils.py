import os
import numpy as np
from io import BytesIO
from PIL import Image, ImageDraw

from python.utils.file_utils import get_extension

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir(os.path.join(".."))


def configure_pil_image(image_path):
    """
    Returns a PIL Image instance configured on 'image_path' and its associated PIL metadata object.
    """
    pil_img = Image.open(image_path)
    image_exif = pil_img.getexif()
    return pil_img, image_exif


def get_mm_per_pixel(image_path, millimeter_height):
    """
    Returns the millimeter per pixel scale of the image located at 'image_path'.
    """
    image = Image.open(image_path)
    pix_height = image.size[1]
    return millimeter_height / pix_height


def get_image_size(image_path):
    """
    Returns the size (bytes) of the image located at 'image_path'.
    """
    with BytesIO() as buffer:
        Image.open(image_path).save(buffer, format=get_extension(image_path).replace('.', '').upper())
        data = buffer.getvalue()
    return len(data)


def resize_to_limit(image_path, size_limit=600000, return_resize_factor=False):
    """
    Resizes the image located at 'image_path' to the given size limit (in bytes), by iteratively reducing both of its
    pixel dimensions by an amount proportional to the difference between its current size and the size limit.
    If 'return_resize_factor' equals True, the ratio (original pixel dimension) / (final pixel dimension),
    which is the same for both the height and width dimensions, is returned.
    """
    pil_img, image_exif = configure_pil_image(image_path)
    original_height = pil_img.size[1]
    aspect = pil_img.size[0] / pil_img.size[1]
    while True:
        with BytesIO() as buffer:
            pil_img.save(buffer, format=get_extension(image_path).replace('.', '').upper())
            data = buffer.getvalue()
        file_size = len(data)
        size_deviation = file_size / size_limit
        if size_deviation <= 1:
            pil_img.save(image_path, exif=image_exif)
            if return_resize_factor is True:
                return pil_img.size[1] / original_height
            break
        else:
            new_width = pil_img.size[0] / (size_deviation ** 0.5)
            new_height = new_width / aspect
            pil_img = pil_img.resize((int(new_width), int(new_height)))


def draw_scale_bars(image_path, scale_bar_length, scale_bar_width, scale_bars_color, min_number=10,
                    parallel_buffer=15, perpendicular_buffer=20, edge_color=(0, 0, 0), edge_width=1,
                    return_max_number=False):
    """
    Draws scale bars along the sides (horizontal and vertical) of the image, alternating such that successive
    scale bars on opposite sides are one gap length apart, and successive scale bars on the same side are two
    gap lengths apart.
        image_path: path to the image on which scale bars will be drawn
        scale_bar_length: length of the scale bars in pixels
        scale_bar_width: width of the scale bars in pixels
        scale_bars_color: scale bars' color in RGB
        min_number: minimum number of vertical or horizontal scale bars drawn (half of this number is drawn
            on the top/bottom or left/right); vertical if the images height is less than its width, horizontal otherwise
        parallel_buffer: the buffer, parallel with respect to the bars' lengths, between the bars and image edges
        perpendicular_buffer: the buffer, parallel with respect to the bars' lengths, between the bars and image edges;
            only relevant to the first and last horizontal and vertical bars drawn
        edge_color: the color of the scale bar's border
        edge_width: the width of the scale bar's border
            Note: by increasing the width, more of the scale bar is converted to 'edge'; the scale bar is not made larger
        return_max_number: True to return the number of scale bars drawn along the maximum dimension
    """
    # Getting a PIL Image instance and storing the image's metadata so that it isn't lost upon rewriting
    pil_img, image_exif = configure_pil_image(image_path)
    # Getting the image's dimensions
    img_width, img_height = pil_img.size
    # Getting an PIL ImageDraw instance (to perform the drawing of scale bars)
    draw = ImageDraw.Draw(pil_img)
    # Finding the minimum and maximum dimensions of the image
    min_dim, max_dim = min([img_width, img_height]), max([img_width, img_height])
    # To find the gap length, we subtract from the minimum image dimension twice the perpendicular buffer (once for each
    # edge) and the length of all scale bars along that dimension and divide by the number of scale bars minus one (since
    # gaps fall between scale bars and scale bars immediate proceed the perpendicular gap on each edge, there is one
    # fewer gap than there are scale bars).
    gap_length = int((min_dim - (2 * perpendicular_buffer) - (min_number * scale_bar_length)) / (min_number - 1))
    # To find the maximum number of scale bars per dimension (that is, the number of scale bars along the maximum
    # dimension), we subtract from the maximum image dimension twice the perpendicular buffer (once for each edge)
    # and the length of one scale bar (so that we may find the greatest number of scale bar / gap pairs), divide by
    # the combined  length of a scale bar a gap, and add one to the result (to account for the scale bar length that
    # we subtracted).
    max_number = int((max_dim - (2 * perpendicular_buffer) - scale_bar_length) / (scale_bar_length + gap_length) + 1)
    # Getting the scale bar parameters for the first horizontal (alternatingly top and bottom) bar to be drawn
    #   x0: rectangle's minimum x-value
    #   x: rectangle's maximum x-value
    #   y0: rectangle's minimum y-value
    #   y: rectangle's maximum y-value
    initial_hor_x0 = perpendicular_buffer
    initial_hor_x = initial_hor_x0 + scale_bar_length
    initial_hor_y0 = parallel_buffer
    initial_hor_y = initial_hor_y0 + scale_bar_width
    # Getting the parameters for and drawing each horizontal and vertical scale bar
    for n in range(max_number):
        # Iterating the Horizontal scale bar parameters
        hor_x0 = initial_hor_x0 + n * (scale_bar_length + gap_length)
        hor_x = hor_x0 + scale_bar_length
        # Reflecting the horizontal scale bar's parameters about the diagonal of the image to get the parameters of
        # the vertical scale bar
        vert_y0 = hor_x0
        vert_y = hor_x
        # If n is even, draw horizontal scale bars along the top of the image and vertical scale bars along the left
        if n % 2 == 0:
            hor_y0 = initial_hor_y0
            hor_y = initial_hor_y
            vert_x0 = hor_y0
            vert_x = hor_y
        # If n is odd, draw horizontal scale bars along the bottom of the image and vertical scale bars along the right
        else:
            hor_y0 = img_height - initial_hor_y0
            hor_y = img_height - initial_hor_y
            # In reflecting, accounting for the fact that the images' dimensions are not necessarily equal, by
            # exchanging the image's height (as in the above assignments) for its width
            vert_x0 = img_width - initial_hor_y
            vert_x = img_width - initial_hor_y0
        # Finding which of the images dimensions are minimum/maximum and identifying scale bar parameters accordingly
        if min_dim == img_height:
            min_scale_bar = [vert_x0, vert_y0, vert_x, vert_y]
            max_scale_bar = [hor_x0, hor_y0, hor_x, hor_y]
        else:
            min_scale_bar = [hor_x0, hor_y0, hor_x, hor_y]
            max_scale_bar = [vert_x0, vert_y0, vert_x, vert_y]
        # Always drawing along the maximum dimension (we are iterating over the number of scale bars along the maximum
        # dimension); only drawing along the minimum dimension if not all of its scale bars have yet been drawn
        draw.rectangle(max_scale_bar, fill=scale_bars_color, outline=edge_color, width=edge_width)
        if n + 1 <= min_number:
            draw.rectangle(min_scale_bar, fill=scale_bars_color, outline=edge_color, width=edge_width)
    # Saving the image with its exif metadata
    pil_img.save(image_path, exif=image_exif)
    # If specified, returning the number of scale bars drawn
    if return_max_number is True:
        return max_number
