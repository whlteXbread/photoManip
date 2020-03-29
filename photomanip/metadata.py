import exiftool


class SetExifTool(exiftool.ExifTool):
    """updates exiftool.ExifTool with capability for writing exif tags."""

    def set_tags(self, tags, filename):
        """sets specified tags for a single file.

        Parameters
        ----------
        tags : list
            contains strings with tags in the format TAG_NAME=TAG_VALUE
        filename : string
            path to image file to be modified

        Returns
        -------
        string
            output from exif writing subprocess
        """
        # Sets specified tags for a single file
        params = [filename]
        args = [f"-{t}" for t in tags]
        params.extend(args)
        params.append("-overwrite_original")
        params = map(exiftool.fsencode, params)
        return self.execute(*params).decode("utf-8")


class ImageExif:
    """class to get and set metadata from photos"""
    metadata_map = {
        "exposure_time": "EXIF:ExposureTime",
        "image_width": "File:ImageWidth",
        "image_height": "File:ImageHeight",
        "keywords": "IPTC:Keywords",
        "date_created": "EXIF:DateTimeOriginal",
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

    def _generate_keyword_set_list(self, keyword_iterable):
        keyword_set_string = self.metadata_map["keywords"] + \
            "+={}"
        return [keyword_set_string.format(item) for item in keyword_iterable]

    def get_metadata_batch(self, filename_list, get_list=None):
        """gets all metadata specified in get_list or self.get_list from all
        files in filename_list

        Parameters
        ----------
        filename_list : list
            contains path-like objects for images
        get_list : list or set, optional
            contains metadata type keys, by default None

        Returns
        -------
        list
            contains dictionaries of image metadata
        """
        # handle case where filenames are path objects
        filename_list = [str(item) for item in filename_list]
        if get_list:
            get_list = self._generate_tag_list(get_list)
        else:
            get_list = self._generate_tag_list(self.get_list)
        with SetExifTool() as et:
            metadata_list = et.get_tags_batch(get_list, filename_list)
        return metadata_list

    def set_image_metadata(self, fname, meta_dict):
        """sets the the metadata specified in mata_dict for the image with
        path fname

        Parameters
        ----------
        fname : string
            path-like string containing path to image file to be modified
        meta_dict : dict
            contains the metadata to be added

        Returns
        -------
        str
            output from the exif-writing subprocess
        """
        # tags/keywords are a special case, handle them first
        keyword_set_list = []
        if "keywords" in meta_dict:
            # remove the keywords from the dict
            keywords = meta_dict.pop("keywords")
            # make a list of keyword-adding commands
            keyword_set_list = self._generate_keyword_set_list(keywords)
        # generate a metedata template dict
        meta_template = self._generate_tag_list(meta_dict.keys(),
                                                set_tags=True)
        # now populate the values in the list
        set_list = [meta_template[k].format(v) for k, v in meta_dict.items()]
        set_list.extend(keyword_set_list)
        with SetExifTool() as et:
            result = et.set_tags(set_list, fname)
        return result  # i guess

    def get_tags_containing(self, keyword_list, search_term):
        """searches for kewords containing search_term in a list of keywords

        Parameters
        ----------
        keyword_list : list
            contains keywords associated with an image
        search_term : str
            substring to search for in all keywouds

        Returns
        -------
        list or str
            list of keywords containing substring if more than one,
            otherwise just the string containing the substring
        """
        tags = [tag for tag in keyword_list if search_term in str(tag)]
        if len(tags) == 1:
            tags = tags[0]
        return tags
