from datetime import datetime

from pathlib import Path
from timeit import default_timer as timer

import click

from photomanip import PAD, CROP
from photomanip.grouper import (
    DAILY_DATETIME_FMT,
    MONTHLY_DATETIME_FMT,
    YEARLY_DATETIME_FMT,
    FileSystemGrouper
)
from photomanip.manipulator import ImageManipulatorCV2
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
        'opencv'
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
        'opencv'
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
        'opencv'
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
        self.manipulator = ImageManipulatorCV2()

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

    def average_photos(self, meta_dict, path_calculator, metadata_calculator):
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
            print(f"working on photos from {date_key}")
            # calculate output dimension
            common_dimension = self.fs_grouper.get_common_dimension(
                self.comb_method,
                meta_list
            )
            # combine the images, write the result
            self.manipulator.combine_images(
                meta_list,
                common_dimension,
                output_name,
                self.comb_method
            )
            # add metadata as appropriate
            calculated_meta = metadata_calculator(
                date_key,
                len(meta_list),
                self.fs_grouper.get_total_exposure(meta_list)
            )
            self.exiftool.set_image_metadata(
                str(output_name),
                calculated_meta
            )
        end = timer()
        return end - start

    def average_by_day(self):
        print("now processing daily images")
        meta_dict = self.fs_grouper.group_by_day()
        elapsed = self.average_photos(
            meta_dict,
            self._calculate_day_avg_path,
            self.metadata_generator.generate_daily_metadata
        )
        print(f"seconds elapsed processing daily images: {elapsed}")

    def average_by_month(self):
        print("now processing monthly images")
        meta_dict = self.fs_grouper.group_by_month()
        elapsed = self.average_photos(
            meta_dict,
            self._calculate_month_avg_path,
            self.metadata_generator.generate_monthly_metadata
        )
        print(f"seconds elapsed processing monthly images: {elapsed}")

    def average_by_year(self):
        print("now processing yearly images")
        meta_dict = self.fs_grouper.group_by_year()
        elapsed = self.average_photos(
            meta_dict,
            self._calculate_year_avg_path,
            self.metadata_generator.generate_yearly_metadata
        )
        print(f"seconds elapsed processing yearly images: {elapsed}")

    def average_all(self):
        pass


@click.command()
@click.option(
    "-i",
    "--image_path",
    help="path of the directory of images you'd like to process",
    required=True,
    type=click.STRING
)
@click.option(
    "-o",
    "--output_path",
    help="path where averages should be placed",
    required=True,
    type=click.STRING
)
@click.option(
    "-c",
    "--combination_method",
    help="""either 'crop' (all images are cropped to smallest dimension) \
            or 'pad' (all images are padded to largest dimension)).\
            Default is `crop`""",
    required=True,
    type=click.STRING,
    default="crop"
)
@click.option(
    "-t",
    "--grouping_tag",
    help="""setting this option will search IPTC keywords for a keyword\
            beginning with the specified string. it will then strip the\
            specified string from the tag and attempt to convert the rest\
            of the keyword to a date. that date will then be used for\
            grouping. Default is None.""",
    required=False,
    type=click.STRING,
    default=None
)
@click.option(
    "-a",
    "--author",
    help="""specifies the author of the generated images. Default is\
         Andrew Catellier.""",
    required=False,
    type=click.STRING,
    default="andrew catellier"
)
def main(image_path, output_path, combination_method, grouping_tag, author):
    """
    Main function to parse commandline arguments and start the averaging
    function.
    """
    metadata_generator = ConstructMetadata(
        author,
        "all rights reserved"
    )
    photo_averager = Averager(
        Path(image_path),
        Path(output_path),
        metadata_generator,
        grouping_tag=grouping_tag,
        comb_method=combination_method
    )
    photo_averager.average_by_day()
    photo_averager.average_by_month()
    photo_averager.average_by_year()


if __name__ == "__main__":
    main()
