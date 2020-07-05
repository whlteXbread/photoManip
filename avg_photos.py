import os

from pathlib import Path

import click

from photomanip.averager import Averager, ConstructMetadata
from photomanip.uploader import FlickrUploader


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
or 'pad' (all images are padded to largest dimension).""",
    show_default=True,
    required=True,
    type=click.Choice(['crop', 'pad'], case_sensitive=False),
    default="crop"
)
@click.option(
    "-t",
    "--grouping_tag",
    help="""setting this option will search IPTC keywords for a keyword \
beginning with the specified string. it will then strip the \
specified string from the tag and attempt to convert the rest \
of the keyword to a date. that date will then be used for \
grouping""",
    show_default=True,
    required=False,
    type=click.STRING,
    default=None
)
@click.option(
    "-a",
    "--author",
    help="""specifies the author of the generated images.""",
    show_default=True,
    required=False,
    type=click.STRING,
    default="andrew catellier"
)
@click.option(
    "-f",
    "--flickr_set_id",
    help="""upload the averages that are generated to the \
specified flickr set.""",
    show_default=True,
    required=False,
    type=click.STRING,
    default=None
)
@click.option(
    "-k",
    "--cache",
    help="""keep a length 2 cache of previously generated monthly and \
yearly averages. depending on image size, cache may use a significant \
amount of storage space (500 MB - 1.5 GB), but greatly decreases \
processing time when generating averages with many images.""",
    show_default=True,
    required=False,
    type=click.BOOL,
    default=True
)
def main(
    image_path,
    output_path,
    combination_method,
    grouping_tag,
    author,
    flickr_set_id,
    cache
):
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
    if cache:
        cwd = os.getcwd()
        default_cache_path = Path(cwd) / '.avg_cache'
        default_cache_path.mkdir(exist_ok=True)
        month_cache = default_cache_path / "monthly"
        year_cache = default_cache_path / "yearly"
    else:
        month_cache = None
        year_cache = None
    # dailies
    daily_average_list = photo_averager.average_by_day()
    if flickr_set_id:
        flickr_uploader = FlickrUploader("./config.yaml")
        for fname in daily_average_list:
            flickr_uploader.upload(fname, flickr_set_id)
    # monthlies
    photo_averager.average_by_month(month_cache)
    # yearly
    photo_averager.average_by_year(year_cache)


if __name__ == "__main__":
    main()
