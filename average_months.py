#! /usr/local/bin/python3
import argparse
import json
from os import path, makedirs
from urllib.parse import urlparse

import flickrapi
import wget

from apikeys import flickrKey, flickrSecret
from avg_phoots import average_dir

ORIGINAL = 'Original'

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
        self.filename = self.picoutdir + '/' + self.fname_maker()
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
        _, fname = path.split(self.source_urls[self.photo_size])
        return fname
    def download(self):
        """Downloads the photo in the size specified by self.photo_size,
         places photo in directory specified by self.picoutdir ."""
        download_url = self.source_urls[self.photo_size]
        parsed_url = urlparse(download_url)
        o_name = path.basename(parsed_url.path)
        if not path.exists(path.join(self.picoutdir, o_name)):
            wget.download(download_url, self.picoutdir)

def download_and_average(flickr_set):
    """Downloads all files in a flickr set with ID flickr_set and stores
     them in folders based on which month they were taken."""
    # real quick make some folders for all the months
    for month in range(1, 13):
        if not path.isdir(str(month)):
            makedirs(str(month))

    # check to see if there's a download log. if there is, load it. if not, initialize it
    json_dl_db = "downloaded_from_" + flickr_set + ".json"
    if not path.exists(json_dl_db):
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
            month_taken = str(int(photo_data.taken[5:7]))
            photo_data.picoutdir = month_taken
            photo_data.download()
            downloaded_images.append(photo.get('id'))
            with open(json_dl_db, 'w') as filename:
                json.dump(downloaded_images, filename)

    # okay, now that we're done with all that, loop through the dirs and make an average.
    for month in range(1, 13):
        average_dir(str(month), 'crop', 'average_of_month_' + str(month) + '.jpg')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("flickr_set",
                        help="the ID of the flickr set you'd like to download and average by month")
    args = parser.parse_args()

    download_and_average(args.flickr_set)
