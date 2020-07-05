import hashlib
import json
import skimage

from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from timeit import default_timer as timer

from photomanip import PAD, CROP
from photomanip.grouper import (
    DAILY_DATETIME_FMT,
    MONTHLY_DATETIME_FMT,
    YEARLY_DATETIME_FMT,
    FileSystemGrouper
)
from photomanip.manipulator import ImageManipulatorSKI
from photomanip.metadata import ImageExif

SOFTWARE_NAME = "photomanip v.0.2.0"
DATETIME_FMT = "%Y:%m:%d %H:%M:%S"


class ConstructMetadata:
    DAILY_TAG_LIST = [
        'avgday:date={date}',
        'avgday:count={count}',
        '{year}',
        'multiple exposure',
        'art',
        'average',
        'python',
    ]
    DAILY_CAPTION = "{count:06} image exposure\r" + \
        "{seconds:.4f} seconds exposed"
    DAILY_TITLE = "avg{date}"
    MONTHLY_TAG_LIST = [
        'avgmonth:date={date}',
        'avgmonth:count={count}'
        '{year}',
        '{month_name}'
        'multiple exposure',
        'art',
        'average',
        'python',
    ]
    MONTHLY_CAPTION = "average of all daily photos published " + \
        "{month_name} {year}\r{count:06} image exposure\r" + \
        "{seconds:.4f} seconds exposed"
    MONTHLY_TITLE = "avg {short_month_name}"
    YEARLY_TAG_LIST = [
        'avgyear:date={year}',
        'avgyear:count={count}',
        '{year}',
        'multiple exposure',
        'art',
        'average',
        'python',
    ]
    YEARLY_CAPTION = "average of all daily photos published " + \
        "in {year}\r{count:06} image exposure\r" + \
        "{seconds:.4f} seconds exposed"
    YEARLY_TITLE = "avg {year}"

    def __init__(self, author, copyright):
        self.author = author
        self.copyright = copyright

    def _generate_daily_tags(self, date, count):
        tag_list = ', '.join(self.DAILY_TAG_LIST)
        tag_list = tag_list.format(
            date=date.strftime(DAILY_DATETIME_FMT),
            count=count,
            year=date.strftime(YEARLY_DATETIME_FMT)
        )
        tag_list = tag_list.split(", ")  # dumb!
        return tag_list

    def _generate_monthly_tags(self, date, count, month_name):
        tag_list = ', '.join(self.MONTHLY_TAG_LIST)
        tag_list = tag_list.format(
            date=date.strftime(MONTHLY_DATETIME_FMT),
            count=count,
            year=date.strftime(YEARLY_DATETIME_FMT),
            month_name=month_name
        )
        tag_list = tag_list.split(", ")  # dumb!
        return tag_list

    def _generate_yearly_tags(self, date, count):
        tag_list = ', '.join(self.YEARLY_TAG_LIST)
        tag_list = tag_list.format(
            year=date.strftime(YEARLY_DATETIME_FMT),
            count=count)
        tag_list = tag_list.split(", ")  # dumb!
        return tag_list

    def generate_daily_metadata(self, date, count, seconds):
        return {
            "name": self.DAILY_TITLE.format(
                date=date.strftime(DAILY_DATETIME_FMT)
            ),
            "caption": self.DAILY_CAPTION.format(
                count=count,
                seconds=seconds
            ),
            "keywords": self._generate_daily_tags(date, count),
            "software": SOFTWARE_NAME,
            "date_created": datetime.now().strftime(DATETIME_FMT),
            "byline": self.author,
            "artist": self.author,
            "copyright_exif": self.copyright,
            "copyright_iptc": self.copyright,
        }

    def generate_monthly_metadata(self, date, count, seconds):
        month_name = date.strftime("%B").lower()
        short_month_name = date.strftime("%b").lower()
        return {
            "name": self.MONTHLY_TITLE.format(
                short_month_name=short_month_name
            ),
            "caption": self.MONTHLY_CAPTION.format(
                month_name=month_name,
                year=date.strftime(YEARLY_DATETIME_FMT),
                count=count,
                seconds=seconds,
            ),
            "keywords": self._generate_monthly_tags(date, count, month_name),
            "software": SOFTWARE_NAME,
            "date_created": datetime.now().strftime(DATETIME_FMT),
            "byline": self.author,
            "artist": self.author,
            "copyright_exif": self.copyright,
            "copyright_iptc": self.copyright,
        }

    def generate_yearly_metadata(self, date, count, seconds):
        return {
            "name": self.YEARLY_TITLE.format(
                year=date.strftime(YEARLY_DATETIME_FMT)
            ),
            "caption": self.YEARLY_CAPTION.format(
                year=date.strftime(YEARLY_DATETIME_FMT),
                count=count,
                seconds=seconds,
            ),
            "keywords": self._generate_yearly_tags(date, count),
            "software": SOFTWARE_NAME,
            "date_created": datetime.now().strftime(DATETIME_FMT),
            "byline": self.author,
            "artist": self.author,
            "copyright_exif": self.copyright,
            "copyright_iptc": self.copyright,
        }


class AverageCache:
    CACHE_NAME = "average_cache.json"

    def __init__(self, metalist, cache_path, fs_grouper, cache_size=2):
        self.reference_metalist = metalist
        self.cache_path = Path(cache_path)
        self.cache_path.mkdir(exist_ok=True, parents=True)
        self.cache_file = cache_path / self.CACHE_NAME
        self.fs_grouper = fs_grouper
        self.cache_size = cache_size
        self.cache_info = self._read_cache(self.cache_file)

    def _sort_cache(self, cache_info):
        return OrderedDict(
                sorted(
                    cache_info.items(),
                    key=lambda item:
                        item[1][self.fs_grouper.exif_datetime_key],
                    reverse=True
                )
            )

    def _read_cache(self, cache_file):
        # read a json file
        if cache_file.exists():
            with open(cache_file) as json_fp:
                cache_info = json.load(json_fp)
            # sort cache_info by created date
            cache_info = self._sort_cache(cache_info)
            return cache_info
        else:
            return dict()

    def _hash_from_metalist(self, metalist):
        # just make a giant string with all the filenames and hash it?
        filenames = [Path(item['SourceFile']).name for item in metalist]
        name_string = ",".join(filenames)
        return hashlib.sha1(name_string.encode()).hexdigest()

    def _calculate_image_filepath(self, hash):
        return self.cache_path / f"{hash[:13]}.tif"

    def _generate_metalist_entry(
        self,
        common_dimension,
        time_exposed,
        num_images,
        cache_image_filename
    ):
        return {
            self.fs_grouper.exif_datetime_key:
                datetime.now().strftime(DATETIME_FMT),
            self.fs_grouper.exif_height_key: common_dimension,
            self.fs_grouper.exif_width_key: common_dimension,
            self.fs_grouper.exp_time_key: time_exposed,
            "num_images": num_images,
            "SourceFile": cache_image_filename,
            "cached": True,
        }

    def _prune_cache(self, cache_info):
        # delete old cache images
        for cache_item in list(cache_info.keys())[self.cache_size:]:
            image_path = Path(cache_info[cache_item]["SourceFile"])
            image_path.unlink()
        # only store the most recent N caches
        return {k: cache_info[k]
                for k in list(cache_info.keys())[:self.cache_size]}

    def _write_image(self, filename, image):
        skimage.io.imsave(filename, image, check_contrast=False)

    def search(self):
        # want to get the latest match for this metalist, if any
        for cache_hash, cache_item in self.cache_info.items():
            # prune the metalist
            images_in_cache = cache_item["num_images"]
            pruned_metalist = self.reference_metalist[:images_in_cache]
            # generate the hash for the pruned metalist
            pruned_hash = self._hash_from_metalist(pruned_metalist)
            if pruned_hash == cache_hash:
                modified_metalist = [cache_item]
                modified_metalist.extend(
                    self.reference_metalist[images_in_cache:]
                )
                return modified_metalist
        # empty cache
        return self.reference_metalist

    def write_cache(
        self,
        cache_image,
        common_dimension,
        time_exposed,
        num_images
    ):
        new_hash = self._hash_from_metalist(self.reference_metalist)
        # write the image to disk
        cache_image_filename = self._calculate_image_filepath(new_hash)
        self._write_image(cache_image_filename, cache_image)
        # add the item to the cache
        new_entry = self._generate_metalist_entry(
            common_dimension,
            time_exposed,
            num_images,
            str(cache_image_filename)
        )
        self.cache_info[new_hash] = new_entry
        # sort by datetime
        self.cache_info = self._sort_cache(self.cache_info)
        # prune old entries
        pruned_cache = self._prune_cache(self.cache_info)
        # write pruned cache to disk
        with open(self.cache_file, "w") as json_fp:
            json.dump(pruned_cache, json_fp)


class Averager:

    def __init__(
        self,
        grouping_path,
        output_path: Path,
        metadata_generator: ConstructMetadata,
        grouping_tag=None,
        comb_method=CROP
    ):
        self.output_path = output_path
        self.output_path.mkdir(exist_ok=True)
        self.comb_method = comb_method
        self.metadata_generator = metadata_generator
        # make an exif setter
        self.exiftool = ImageExif()
        # build grouper
        self.grouping_tag = grouping_tag
        self.fs_grouper = FileSystemGrouper(grouping_path, grouping_tag)
        # instantiate manipulator
        self.manipulator = ImageManipulatorSKI()

    def _calculate_day_avg_path(self, date_key, meta_list=None):
        date = date_key.strftime(DAILY_DATETIME_FMT)
        fname = f"{date}.jpg"
        month_number = date_key.strftime('%m')
        month_path = self.output_path / month_number
        month_path.mkdir(exist_ok=True)
        return month_path / fname

    def _calculate_month_avg_path(self, date_key, meta_list=None):
        fname_stem = date_key.strftime(MONTHLY_DATETIME_FMT)
        if meta_list:
            # i guess find the date of the first and last items?
            first_date = self.fs_grouper.date_extractor(
                meta_list[0],
                self.grouping_tag,
                DAILY_DATETIME_FMT
            )
            first_date = first_date.strftime("%d")
            last_date = self.fs_grouper.date_extractor(
                meta_list[-1],
                self.grouping_tag,
                DAILY_DATETIME_FMT
            )
            last_date = last_date.strftime("%d")
            suffix = f"_{first_date}-{last_date}"
        else:
            suffix = ""
        fname = f"{fname_stem}{suffix}.jpg"
        return self.output_path / fname

    def _calculate_year_avg_path(self, date_key, meta_list=None):
        fname_stem = date_key.strftime(YEARLY_DATETIME_FMT)
        if meta_list:
            # i guess find the date of the first and last items?
            first_date = self.fs_grouper.date_extractor(
                meta_list[0],
                self.grouping_tag,
                DAILY_DATETIME_FMT
            )
            first_date = first_date.strftime("%m-%d")
            last_date = self.fs_grouper.date_extractor(
                meta_list[-1],
                self.grouping_tag,
                DAILY_DATETIME_FMT
            )
            last_date = last_date.strftime("%m-%d")
            suffix = f"_{first_date}_{last_date}"
        else:
            suffix = ""
        fname = f"{fname_stem}{suffix}.jpg"
        return self.output_path / fname

    def _calculate_num_images(self, metalist):
        count = 0
        for item in metalist:
            if "num_images" in item:
                count += item["num_images"]
            else:
                count += 1
        return count

    def average_photos(
        self,
        meta_dict,
        path_calculator,
        metadata_calculator,
        cache_path=None
    ):
        average_images = []
        start = timer()
        for date_key, meta_list in meta_dict.items():
            if len(meta_list) == 1:
                print(f"only one photo for {date_key}, skipping")
                continue
            # calculate output name
            output_name = path_calculator(date_key, meta_list)
            # has this image already been generated?
            if output_name.exists():
                print(f"file {output_name} already generated, skipping")
                continue
            # store filename for bookkeeping
            average_images.append(output_name)
            print(f"working on photos from {date_key}")
            if cache_path:
                # check if we have a valid cache entry
                avg_cacher = AverageCache(
                    meta_list,
                    cache_path,
                    self.fs_grouper
                )
                meta_list = avg_cacher.search()
            # calculate output dimension
            common_dimension = self.fs_grouper.get_common_dimension(
                self.comb_method,
                meta_list
            )
            num_images = self._calculate_num_images(meta_list)
            exposure_time = self.fs_grouper.get_total_exposure(meta_list)
            # combine the images, write the result
            combined = self.manipulator.combine_images(
                meta_list,
                common_dimension,
                num_images,
                output_name,
                self.comb_method
            )
            # add metadata as appropriate
            calculated_meta = metadata_calculator(
                date_key,
                num_images,
                exposure_time
            )
            # add this item to our cache, if there's a cache dir
            if cache_path:
                avg_cacher.write_cache(
                    combined,
                    common_dimension,
                    exposure_time,
                    num_images
                )
            self.exiftool.set_image_metadata(
                str(output_name),
                calculated_meta
            )
        end = timer()
        return end - start, average_images

    def average_by_day(self, cache_dir=None):
        print("now processing daily images")
        meta_dict = self.fs_grouper.group_by_day()
        elapsed, image_list = self.average_photos(
            meta_dict,
            self._calculate_day_avg_path,
            self.metadata_generator.generate_daily_metadata,
            cache_dir
        )
        print(f"seconds elapsed processing daily images: {elapsed}")
        return image_list

    def average_by_month(self, cache_dir=None):
        print("now processing monthly images")
        meta_dict = self.fs_grouper.group_by_month()
        elapsed, image_list = self.average_photos(
            meta_dict,
            self._calculate_month_avg_path,
            self.metadata_generator.generate_monthly_metadata,
            cache_dir
        )
        print(f"seconds elapsed processing monthly images: {elapsed}")
        return image_list

    def average_by_year(self, cache_dir=None):
        print("now processing yearly images")
        meta_dict = self.fs_grouper.group_by_year()
        elapsed, image_list = self.average_photos(
            meta_dict,
            self._calculate_year_avg_path,
            self.metadata_generator.generate_yearly_metadata,
            cache_dir
        )
        print(f"seconds elapsed processing yearly images: {elapsed}")
        return image_list

    def average_all(self):
        raise NotImplementedError()
