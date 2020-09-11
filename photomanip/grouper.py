from collections import defaultdict, OrderedDict
from datetime import datetime
from pathlib import Path

from photomanip import PAD, CROP, RESIZE
from photomanip.metadata import ImageExif

DATETIME_FMT = "%Y:%m:%d %H:%M:%S"
DAILY_DATETIME_FMT = "%Y%m%d"
MONTHLY_DATETIME_FMT = "%Y%m"
YEARLY_DATETIME_FMT = "%Y"


class Grouper:
    def __init__(self, *args, **kwargs):
        self.metadata_list = None

    def date_extractor(self, keyword_grouper=None):
        raise NotImplementedError()

    def _height_width_extractor(self, metadata):
        raise NotImplementedError()

    def get_photo_list(self):
        raise NotImplementedError()

    def group_by_day(self):
        raise NotImplementedError()

    def group_by_month(self):
        raise NotImplementedError()

    def group_by_year(self):
        raise NotImplementedError()

    def get_common_dimension(self, combination_method):
        raise NotImplementedError()


class FileSystemGrouper(Grouper):
    def __init__(self, image_directory, grouping_tag=None,
                 grouping_fmt=DAILY_DATETIME_FMT, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_folder_path = Path(image_directory)
        self.exif_reader = ImageExif()
        self.exif_datetime_key = self.exif_reader.metadata_map["date_created"]
        self.exif_keywords_key = self.exif_reader.metadata_map["keywords"]
        self.exif_height_key = self.exif_reader.metadata_map["image_height"]
        self.exif_width_key = self.exif_reader.metadata_map["image_width"]
        self.exp_time_key = self.exif_reader.metadata_map["exposure_time"]
        self.photo_list = self.get_photo_list()
        self.metadata_list = \
            self.exif_reader.get_metadata_batch(self.photo_list)
        self.grouping_tag = grouping_tag
        self.datetime_dict = self.build_datetime_dict(
            grouping_tag,
            grouping_fmt
        )

    def date_extractor(
        self,
        metadata,
        keyword_grouper=None,
        grouping_fmt=None
    ):
        if keyword_grouper:
            # does the image have keywords?
            if self.exif_keywords_key in metadata:
                # is there a match for the grouper in the keywords?
                matches = self.exif_reader.get_tags_containing(
                    metadata[self.exif_keywords_key],
                    keyword_grouper
                )
                if isinstance(matches, str):
                    # convert to datetime
                    matches = matches.replace(keyword_grouper, '')
                    return datetime.strptime(matches, grouping_fmt)
        # get the date created from exif and gooooo
        exif_datetime = metadata[self.exif_datetime_key]
        return datetime.strptime(exif_datetime, DATETIME_FMT)

    def _height_width_extractor(self, metadata_list):
        image_heights = [item[self.exif_height_key] for item in metadata_list]
        image_widths = [item[self.exif_width_key] for item in metadata_list]
        return image_heights, image_widths

    def _exposure_time_extractor(self, metadata_list):
        exposure_times = [item[self.exp_time_key] for item in metadata_list]
        return exposure_times

    def build_datetime_dict(self, grouping_tag, grouping_fmt):
        datetime_dict = defaultdict(list)
        for metadata in self.metadata_list:
            this_date = self.date_extractor(metadata,
                                            keyword_grouper=grouping_tag,
                                            grouping_fmt=grouping_fmt)
            datetime_dict[this_date].append(metadata)
        datetime_dict = OrderedDict(sorted(datetime_dict.items()))
        return datetime_dict

    def get_photo_list(self, extension='.jpg'):
        """
        Gets a list of files with extension `extension` (default '.jpg') in
        a folder.
        """
        # find all files with the matching extension recursively
        onlyfiles = \
            sorted(list(self.image_folder_path.glob(f'**/*{extension}')))
        # resolve full paths
        onlyfiles = [item.resolve() for item in onlyfiles]
        return onlyfiles

    def group_by_day(self):
        grouped = defaultdict(list)
        for date, meta in self.datetime_dict.items():
            new_key = datetime(date.year, date.month, date.day)
            if len(meta) > 1:
                grouped[new_key].extend(meta)
            else:
                grouped[new_key].append(meta[0])
        return grouped

    def group_by_month(self):
        grouped = defaultdict(list)
        for date, meta in self.datetime_dict.items():
            new_key = datetime(date.year, date.month, 1)
            if len(meta) > 1:
                grouped[new_key].extend(meta)
            else:
                grouped[new_key].append(meta[0])
        return grouped

    def group_by_year(self):
        grouped = defaultdict(list)
        for date, meta in self.datetime_dict.items():
            new_key = datetime(date.year, 1, 1)
            if len(meta) > 1:
                grouped[new_key].extend(meta)
            else:
                grouped[new_key].append(meta[0])
        return grouped

    def group_by_month_progressive(self):
        grouped = defaultdict(list)
        start_date = next(iter(self.datetime_dict.keys()))
        # scary time complex loop, but we have a cache for the image processing
        # operations
        for stop_date in self.datetime_dict.keys():
            current_month = stop_date.month
            new_key = datetime(stop_date.year, stop_date.month, stop_date.day)
            # if we've moved on to the next month, update start date
            if not start_date.month == current_month:
                start_date = stop_date
            for date, meta in self.datetime_dict.items():
                if date >= start_date and date <= stop_date:
                    if len(meta) > 1:
                        grouped[new_key].extend(meta)
                    else:
                        grouped[new_key].append(meta[0])
        return grouped

    def group_by_year_progressive(self):
        grouped = defaultdict(list)
        start_date = next(iter(self.datetime_dict.keys()))
        # scary time complex loop, but we have a cache for the image processing
        # operations
        for stop_date in self.datetime_dict.keys():
            current_year = stop_date.year
            new_key = datetime(stop_date.year, stop_date.month, stop_date.day)
            # if we've moved on to the next year, update start date
            if not start_date.year == current_year:
                start_date = stop_date
            for date, meta in self.datetime_dict.items():
                if date >= start_date and date <= stop_date:
                    if len(meta) > 1:
                        grouped[new_key].extend(meta)
                    else:
                        grouped[new_key].append(meta[0])
        return grouped

    def get_common_dimension(self, comb_method, metadata_list):
        """Computes the dimensions of the final output image based on specified
        combination method and lists of images widths and heights."""
        image_heights, image_widths = \
            self._height_width_extractor(metadata_list)
        if comb_method == PAD or comb_method == RESIZE:
            max_w = max(image_widths)
            max_h = max(image_heights)
            expand_to = max(max_w, max_h)
            if (expand_to % 2) == 1:
                expand_to -= 1
            return expand_to
        elif comb_method == CROP:
            min_w = min(image_widths)
            min_h = min(image_heights)
            crop_to = min(min_w, min_h)
            if (crop_to % 2) == 1:
                crop_to -= 1
            return crop_to
        else:
            raise ValueError('invalid value for combination_method')

    def get_total_exposure(self, metadata_list):
        exposure_time_list = self._exposure_time_extractor(metadata_list)
        return sum(exposure_time_list)


class FlickrGrouper(Grouper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        raise NotImplementedError()
