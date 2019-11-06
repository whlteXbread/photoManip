from datetime import datetime

import exiftool

SOFTWARE_NAME = "photomanip v.0.1.0"
DATETIME_FMT = "%Y:%m:%d %H:%M:%S"


class SetExifTool(exiftool.ExifTool):

    def set_tags(self, tags, filename):
        """Sets specified tags for a single file"""
        params = [filename]
        args = ["-" + t for t in tags]
        params.extend(args)
        params = map(exiftool.fsencode, params)
        return self.execute(*params).decode("utf-8")


class ImageExif:
    metadata_map = {
        "exposure_time": "EXIF:ExposureTime",
        "image_width": "File:ImageWidth",
        "image_height": "File:ImageHeight",
        "keywords": "IPTC:Keywords",
        "date_created": "Composite:DateTimeCreated",
        "caption": "IPTC:Caption-Abstract",
        "name": "IPTC:ObjectName",
        "software": "EXIF:Software",
        "byline": "IPTC:By-Line",
        "artist": "EXIF:Artist",
        "copyright_exif": "EXIF:Copyright",
        "copyright_iptc": "IPTC:Copyright",
    }
    GET_EXIF_TAG_SET = {
        "exposure_time",
        "image_width",
        "image_height",
        "keywords",
        "date_created",
    }
    SET_EXIF_TAG_SET = {
        "keywords",
        "caption",
        "name",
        "software",
        "date_created",
        "byline",
        "artist",
        "copyright_exif",
        "copyright_iptc",
    }

    def __init__(self, *args, **kwargs):
        self.artist = ""
        self.copyright = ""
        if 'set_list' in kwargs:
            self.set_list = kwargs['set_list']
        else:
            self.set_list = self.SET_EXIF_TAG_SET

        if "get_list" in kwargs:
            self.get_list = kwargs["get_list"]
        else:
            self.get_list = self.GET_EXIF_TAG_SET

    def _generate_tag_list(self, tag_iterable=None, set_tags=False):
        if set_tags:
            return {item: self.metadata_map[item] + "={}"
                    for item in tag_iterable}
        else:
            return [self.metadata_map[item] for item in tag_iterable]

    def get_metadata_batch(self, filename_list, get_list=None):
        # TODO: HANDLE CASE WHEN FILENAMES ARE PATH OBJECTS
        if get_list:
            get_list = self._generate_tag_list(get_list)
        else:
            get_list = self._generate_tag_list(self.get_list)
        with SetExifTool() as et:
            metadata_list = et.get_tags_batch(get_list, filename_list)
        return metadata_list

    def set_image_metadata(self, fname, meta_dict):
        # generate a metedata template dict
        meta_template = self._generate_tag_list(meta_dict.keys(), set_tags=True)
        # now populate the values in the list
        set_list = [meta_template[k].format(v) for k, v in meta_dict.items()]
        with SetExifTool() as et:
            result = et.set_tags(set_list, fname)
        return result  # i guess

    def get_tags_containing(self, keyword_list, search_term):
        tags = [tag for tag in keyword_list if search_term in str(tag)]
        if len(tags) == 1:
            tags = tags[0]
        return tags
