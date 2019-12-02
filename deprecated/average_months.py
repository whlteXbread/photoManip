import argparse
import json
import os

from collections import defaultdict, OrderedDict
from datetime import date
from timeit import default_timer as timer
from urllib.parse import urlparse

import click
import flickrapi
import wget

from apikeys import flickrKey, flickrSecret
from photomanip.avg_phoots import (CROP, COMBINATION_METHODS, set_image_metadata, average_each_day,
    ImageTools, get_phoot_list, get_final_dimension)

ORIGINAL = 'Original'

AVG_MONTH_TAG_LIST = ['multiple exposure',
                      'art',
                      'average',
                      'python',
                      'opencv']

AVG_MONTH_CAPTION = 'average of all daily photos published {} {}\\n\\ntotal exposure time in seconds: {}'

# instantiate the flickrAPI object
flickr_api = flickrapi.FlickrAPI(flickrKey, flickrSecret, cache=True)
class PicInfo(object):
    """This class will store information about pics downloaded from flickr
     and download the file that was originally uploaded to flickr."""
    picoutdir = 'imageDL'
    photo_size = ORIGINAL
    def __init__(self, flickr_spec):
        self.flickr_spec = flickr_spec
        self.source_urls = self.url_maker()
        self.filename = os.path.join(self.picoutdir, self.fname_maker())
        self.flickr_id = flickr_spec.get('id')
        deets = flickr_api.photos_getInfo(photo_id=flickr_spec.get('id'))
        self.taken = deets.find('photo').find('dates').attrib['taken']
    def url_maker(self):
        """Generates the download URL for each photo size."""
        sizes = flickr_api.photos_getSizes(photo_id=self.flickr_spec.get('id'))
        out_dict = {}
        for size_element in sizes.find('sizes').findall('size'):
            label = size_element.attrib['label']
            url = size_element.attrib['source']
            out_dict[label] = url
        return out_dict
    def fname_maker(self):
        """Generates the filename for storage on the local system."""
        _, fname = os.path.split(self.source_urls[self.photo_size])
        return fname
    def download(self):
        """Downloads the photo in the size specified by self.photo_size,
         places photo in directory specified by self.picoutdir ."""
        download_url = self.source_urls[self.photo_size]
        parsed_url = urlparse(download_url)
        o_name = os.path.basename(parsed_url.path)
        if not os.path.exists(os.path.join(self.picoutdir, o_name)):
            wget.download(download_url, self.picoutdir)

def make_month_folders(out_path):
    """makes a folder for each month of the year in specified path"""
    # real quick make some folders for all the months
    dir_list = []
    for month in range(1, 13):
        month_str = os.path.join(out_path,
                                 date(1984, month, 1).strftime('%B').lower())
        dir_list.append(month_str)
        if not os.path.isdir(month_str):
            os.makedirs(month_str)
    return dir_list

def download_and_average(flickr_set, outdir_prefix='avgmonths'):
    """Downloads all files in a flickr set with ID flickr_set and stores
     them in folders based on which month they were taken."""
    # real quick make some folders for all the months
    dir_list = make_month_folders(outdir_prefix)

    # check to see if there's a download log. if there is, load it. if not, initialize it
    json_dl_db = "downloaded_from_" + flickr_set + ".json"
    if not os.path.exists(json_dl_db):
        downloaded_images = []
    else:
        with open(json_dl_db, 'r') as filename:
            downloaded_images = json.load(filename)

    # first walk the set and get all the photos from the set
    for photo in flickr_api.walk_set(flickr_set):
        if photo.get('id') in downloaded_images:
            print(photo.get('id') + " already downloaded")
        else:
            print("\ndownloading " + photo.get('id') + "\n")
            photo_data = PicInfo(photo)
            month_taken = date(1984, int(photo_data.taken[5:7]), 1).strftime('%B').lower()
            photo_data.picoutdir = os.path.join(outdir_prefix, month_taken)
            photo_data.download()
            downloaded_images.append(photo.get('id'))
            with open(json_dl_db, 'w') as filename:
                json.dump(downloaded_images, filename)

    # okay, now that we're done with all that, loop through the dirs and make an average.
    for month in dir_list:
        average_each_day(month, 'crop', month + '_days')

def group_photos_by_month(photo_list, grouping_tag='faceit365'):
    # loop through all the files and make a dict to key track of things
    photo_info_by_month = defaultdict(list)

    # now loop through the list of files and get exposure times and max dimensions
    for fname in photo_list:
        current_image = ImageTools(fname, 'pil')
        grouping_tags = current_image.get_tags_containing(grouping_tag)
        if any(grouping_tags):
            month_key = grouping_tags[-8:-2]
        else:
            image_date = current_image.exif_data['DateTimeOriginal']
            month_key = image_date[:-11].replace(':', '')
        photo_info_by_month[month_key].append(
            {'filename': fname,
             'exposure_time': current_image.exposure_time_in_s,
             'hxw': (current_image.width, current_image.height)})
    
    # sort the dict so the averages are generated in order
    photo_info_by_month = OrderedDict(sorted(photo_info_by_month.items()))

    return photo_info_by_month

def get_aggregate_photo_data(photo_list):
    filenames = []
    widths = []
    heights = []
    exposure_times = []
    total_shutter_open = 0
    for photo in photo_list:
        filenames.append(photo['filename'])
        widths.append(photo['hxw'][0])
        heights.append(photo['hxw'][1])
        exposure_times.append(photo['exposure_time'])
        total_shutter_open += photo['exposure_time']
    
    return filenames, widths, heights, exposure_times, total_shutter_open

def generate_avgmonth_metadata(year, month, total_shutter_open,
                               num_images):

    long_month = date(1984, int(month), 1).strftime('%B').lower()
    short_month = date(1984, int(month), 1).strftime('%b').lower() 
    caption = AVG_MONTH_CAPTION.format(long_month, year, total_shutter_open)
    title = 'avg {}'.format(short_month)
    out_tag_list = AVG_MONTH_TAG_LIST.copy()
    out_tag_list.append(year)
    out_tag_list.append(long_month)
    
    out_tag_list.append('avgmonth:count={}'.format(num_images))
    out_tag_list.append('avgmonth:date={}{}'.format(year, month))

    return caption, title, out_tag_list

def average_from_folder_by_month(image_folder_path, outdir_prefix='avgmonths',
                                 library='cv2', comb_method=CROP,
                                 byline='', copyright_str='all_rights_reserved'):
    """Organizes all images in a folder into months and make an average
    for all images in each month found"""

    # get a list of all the photos to process
    photo_list = get_phoot_list(image_folder_path)
    
    # separate them out into different lists by month
    grouped_by_month = group_photos_by_month(photo_list)

    start = timer()
    print("using {} for image processing".format(library))
    print("now processing daily images")
    combine_function = COMBINATION_METHODS[library]

    for date, photo_list in grouped_by_month.items():
        num_images = len(photo_list)
        if num_images == 1:
            print("only one photo for {}, skipping".format(date))
            continue
        
        current_month = date[4:6]
        current_year = date[:4]

        out_name = os.path.join(outdir_prefix, 'avg{}.jpg'.format(date))
        # do a quick check to see if this image has already been generated
        if os.path.isfile(out_name):
            print("file {} already generated".format(out_name))
            continue
        
        filenames, widths, heights, _, total_shutter_open = \
            get_aggregate_photo_data(photo_list)
        
        output_dimension = get_final_dimension(comb_method, widths, heights)

        combine_function(filenames, comb_method, output_dimension, out_name)
        
        caption, title, tag_list = generate_avgmonth_metadata(
            current_year, current_month, total_shutter_open, num_images)
        
        set_image_metadata(out_name, tag_list, caption, title, byline,
                           copyright_str)
    
    end = timer()
    print("processing time in seconds: {}".format(end - start))


@click.command()
@click.option('-f', '--folder', help="the folder from which to generate average months", 
              required=False, default=None, type=click.STRING)
@click.option('-s', '--flickr_set', help="the flickr set id to download and then generate average months",
              required=False, default=None, type=click.STRING)
@click.option('-b', '--byline', help="the author to specify for image metadata",
              required=False, default='', type=click.STRING)
@click.option('-o', '--out_dir', help="folder in which to write averages. default is `avgmonths`",
              required=False, default='avgmonths', type=click.STRING)
def main(folder, flickr_set, byline, out_dir):
    if folder and flickr_set:
        raise ValueError("set either folder or flickr set")
    if folder:
        average_from_folder_by_month(folder, byline=byline, outdir_prefix=out_dir)
    if flickr_set:
        download_and_average(flickr_set, outdir_prefix=out_dir)

if __name__ == "__main__":
    main()