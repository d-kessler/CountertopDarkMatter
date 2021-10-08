
# EXPERIMENT SUBJECTS

# Minimum height and width (inches) that could result from an image being cropped into four parts
# NOTE: the height dimension is assumed to be the smaller dimension
min_shorter_image_dimension_in = 4
min_longer_image_dimension_in = 5
# Scale bar parameters
scale_bar_length_mm = 1  # millimeters
scale_bar_width_mm = 1  # millimeters
# Interior color
scale_bars_color = (0, 255, 0)  # (green)
# The number drawn along the minimum image dimension
scale_bars_min_number = 10
# The distance between the scale bar and image edge, perpendicular to the scale bar's length
# (only relevant to first and last bar)
scale_bars_perpendicular_buffer = 2  # millimeters
# The distance between the scale bar and image edge, parallel to the scale bar's length
scale_bars_parallel_buffer = 1  # millimeters
# The color of the scale bar's boarder
scale_bar_edge_color = (0, 0, 0)  # (black)
# The edge of the scale bar's border; greater <=> more of the scale bar is 'edge' (overall size does not increase)
scale_bars_edge_with = 2  # pixels

# SIMULATION SUBJECTS
# Number of simulations made per second folder
simulations_per_second_folder = 5
# Range of possible ellipse semi-minor axes in millimeters (np.arange parameters)
min_sim_minor_axis_mm = 1
max_sim_minor_axis_mm = 6
sim_minor_axis_step_mm = 1
# Maximum major axis size (selections larger default to this size)
max_sim_major_axis_mm = 25.4  # 1 inch
# Minimum and maximum radii of the regular polygons drawn around the edges of simulations
min_sim_edge_poly_rad_mm = 0.475
max_sim_edge_poly_rad_mm = 0.525
# Maximum and minimum number of sides of the regular polygons drawn around the edges of simulations
min_sim_edge_poly_sides = 6
max_sim_edge_poly_sides = 8

# MARKING SUBJECTS
# Number of pixels between marking images' edges and the consensus marking
marking_edge_buffer_pixels = 30
# Factor by which promoted features' cropped images are enlarged
marking_image_enlarge_factor = 3
# Angular extent in degrees of consensus markings' edge gaps
marking_border_gaps_angular_extent = 0
# Angular extent in degrees of consensus markings' line segments
marking_border_segments_angular_extent = 5
# Opacity of consensus markings' line segments
marking_border_opacity = 0.30
# Color of consensus markings' line segments
marking_border_color = (255, 255, 255)
# Thickness of consensus markings' line segments
marking_border_thickness = 1
