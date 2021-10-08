import os
from PIL import Image, ExifTags
from datetime import datetime

# Ensuring that the current working directory is "CountertopDarkMatter"
while os.getcwd()[-20:] != "CountertopDarkMatter":
    os.chdir(os.path.join(".."))


class ImageExif:

    def __init__(self, image_file_path):
        pil_image = Image.open(image_file_path)
        pil_image_exif = pil_image.getexif()
        self.image_exif_dict = self.get_image_exif_dict(pil_image_exif)

    @staticmethod
    def get_image_exif_dict(pil_image_exif):
        return {ExifTags.TAGS[k]: j for k, j in pil_image_exif.items() if k in ExifTags.TAGS}

    def get_gps_exif(self):
        gps_dict = {}
        try:
            for key in self.image_exif_dict['GPSInfo'].keys():
                gps_tag = ExifTags.GPSTAGS.get(key)
                gps_dict[gps_tag] = self.image_exif_dict['GPSInfo'][key]
            latitude_dms = gps_dict.get('GPSLatitude')
            longitude_dms = gps_dict.get('GPSLongitude')
            latitude_ref = gps_dict.get('GPSLatitudeRef')
            longitude_ref = gps_dict.get('GPSLongitudeRef')
            if latitude_ref == "S":
                latitude = -abs(self.get_decimal_from_dms(latitude_dms))
            else:
                latitude = self.get_decimal_from_dms(latitude_dms)
            if longitude_ref == "W":
                longitude = -abs(self.get_decimal_from_dms(longitude_dms))
            else:
                longitude = self.get_decimal_from_dms(longitude_dms)
        except KeyError:
            latitude, longitude = None, None
        return latitude, longitude

    @staticmethod
    def get_decimal_from_dms(dms):
        degrees = dms[0]
        minutes = dms[1] / 60.0
        seconds = dms[2] / 3600.0
        return degrees + (minutes / 60.0) + (seconds / 3600.0)

    def get_date_exif(self):
        try:
            date_exif = datetime.strptime(
                self.image_exif_dict['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S').strftime('%m:%d:%Y %H:%M:%S')
        except KeyError:
            date_exif = None
        return date_exif
