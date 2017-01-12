import flickrapi
import wget
from os import path, walk, remove, makedirs
from urlparse import urlparse
import json
from datetime import date, datetime, timedelta
from apikeys import *
from avgPhoots import *

import urllib3.contrib.pyopenssl

# instantiate the flickrAPI object
flickrAPI = flickrapi.FlickrAPI(flickrKey, flickrSecret, cache=True)
class picinfo(object):
  """This class will store information about pics downloaded from flickr."""
  picoutdir = 'imageDL'
  def __init__(self,flickrSpec):
    self.photo_size = 'Original'
    self.flickrSpec = flickrSpec
    self.sourceUrls = self.urlMaker()
    self.filename = self.picoutdir + '/' + self.fnameMaker()
    self.flickrID = flickrSpec.get('id')
    deets = flickrAPI.photos_getInfo(photo_id=flickrSpec.get('id'))
    self.taken = deets.find('photo').find('dates').attrib['taken']
  def urlMaker(self):
    sizes = flickrAPI.photos_getSizes(photo_id=self.flickrSpec.get('id'))
    out_dict = {}
    for size_element in sizes.find('sizes').findall('size'):
      label = size_element.attrib['label']
      url = size_element.attrib['source']
      out_dict[label] = url
    return out_dict
  def fnameMaker(self):
    urlstub, fname = path.split(self.sourceUrls[self.photo_size])
    return fname
  def downloadOriginal(self):
    download_url = self.sourceUrls[self.photo_size]
    parsed_url = urlparse(download_url)
    o_name = path.basename(parsed_url.path)
    if not path.exists(path.join(self.picoutdir,o_name)):
      wget.download(download_url,self.picoutdir)

def download_and_average(flickrSet):
  # real quick make some folders for all the months
  for month in range(1,13):
    if not path.isdir(str(month)):
      makedirs(str(month))
  
  # check to see if there's a download log. if there is, load it. if not, initialize it
  jsonDLDB = "downloaded_from_" + flickrSet + ".json"
  if not path.exists(jsonDLDB):
    downloaded_images = []
  else: 
    with open(jsonDLDB,'r') as f:
      downloaded_images = json.load(f)
  
  # first walk the set and get all the photos from the set
  for photo in flickrAPI.walk_set(flickrSet):
    if photo.get('id') in downloaded_images:
      print photo.get('id') + " already downloaded"
    else:
      print "\ndownloading " + photo.get('id') + "\n"
      photo_data = picinfo(photo)
      month_taken = str(int(photo_data.taken[5:7]))
      photo_data.picoutdir = month_taken
      photo_data.downloadOriginal()
      downloaded_images.append(photo.get('id'))
      with open(jsonDLDB,'w') as f:
        all_downloaded = json.dump(downloaded_images,f)
  
  # okay, now that we're done with all that, loop through the dirs and make an average.
  for month in range(1,13):
    average_dir(str(month),'crop','average_of_month_' + str(month) + '.jpg')

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("flickrSet", help="the ID of the flickr set you'd like to download and average by month")
  args = parser.parse_args()
  
  download_and_average(args.flickrSet)