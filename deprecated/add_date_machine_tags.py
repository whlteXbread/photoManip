#! /usr/local/bin/python3
import argparse
from datetime import datetime
from os import path
from urllib.parse import urlparse

import flickrapi
import wget

from apikeys import flickrKey, flickrSecret

ORIGINAL = 'Original'
READ_FMT = '%m-%d-%Y'
WRITE_FMT = '%Y%m%d'

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
        self.tag_list = []
        tags_object = deets.find('photo').find('tags')
        for tag_element in tags_object:
            self.tag_list.append(tag_element.attrib['raw'])
        self.tag_list = ['"' + tag + '"' for tag in self.tag_list]
        self.title = deets.find('photo').find('title').text
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

def add_date_machine_tag(flickr_set, namespace, predicate):
    """Adds a machine tag with a specified namespace and predicate and a value
       in the format YYYYMMDD where YYYYMMDD is the date the photo was taken.
    """
    counter = 0
    # first walk the set and get all the photos from the set
    for photo in flickr_api.walk_set(flickr_set):
        photo_data = PicInfo(photo)
        # the following works when you want to use the date taken, but I'm a cheater i guess
        # value = photo_data.taken[:10].replace('-', '')
        # the following works when you want to use a date set as the title
        try:
            specified_date = datetime.strptime(photo_data.title, READ_FMT)
        except ValueError:
            print("\n{} not a valid title—please add machine tag to {} manually.\n"\
                .format(photo_data.title, photo.get('id')))
            continue
        value = specified_date.strftime(WRITE_FMT)
        machine_tag = '"' + namespace + ':' + predicate + '=' + value + '"'
        if not machine_tag in photo_data.tag_list:
            print("\nadding machine tag {} to {} \n".format(machine_tag, photo.get('id')))
            # cool thing about `photos.setTags()`—it clobbers existing tags.
            # so you have to get the current tags and append your new machine tag to the list.
            new_tag_list = photo_data.tag_list
            new_tag_list.append(machine_tag)
            tag_string = ' '.join(new_tag_list)
            flickr_api.photos_setTags(photo_id=photo.get('id'), tags=tag_string)
            counter += 1
        else:
            print("\n{} already a machine tag for {}. not adding.\n"\
                .format(machine_tag, photo.get('id')))
    print("{} machine tags added.".format(counter))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("flickr_set",
                        help="the ID of the flickr set you'd like to download and average by month")
    parser.add_argument("namespace",
                        help="the namespace of the machine tag you'd like to add")
    parser.add_argument("predicate",
                        help="the predicate of the machine tag you'd like to add")
    args = parser.parse_args()

    add_date_machine_tag(args.flickr_set, args.namespace, args.predicate)
    # add_date_machine_tag('72157653267834936', 'faceit365', 'date')
