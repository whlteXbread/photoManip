#! /usr/bin/python
from PIL import Image as Im
from PIL import ImageOps as ImOps
from PIL import ImageMath as ImMath
from PIL.ExifTags import TAGS
from os import listdir
from os.path import isfile, join
import argparse
import operator

EXPOSURE_TIME = 'ExposureTime'
LANDSCAPE = 'landscape'
PORTRAIT = 'portrait'
SQUARE = 'square'
PAD = 'pad'
CROP = 'crop'

# code sample from http://effbot.org/zone/pil-histogram-equalization.htm -------
def equalize(h):
  lut = []
  for b in range(0, len(h), 256):
    # step size
    step = reduce(operator.add, h[b:b + 256]) / 255
    # create equalization lookup table
    n = 0
    for i in range(256):
      lut.append(n / step)
      n = n + h[i + b]
  return lut
# code sample from http://effbot.org/zone/pil-histogram-equalization.htm -------


def get_exposure_time_in_s(fn):
  ret = {}
  i = Im.open(fn)
  info = i._getexif()
  for tag, value in info.items():
      decoded = TAGS.get(tag, tag)
      ret[decoded] = value
  exposure_time = ret[EXPOSURE_TIME]
  exposure_time_in_s = (float(exposure_time[0])) / (float(exposure_time[1]))
  return exposure_time_in_s


def get_phoot_list(dir_name):
  onlyfiles = [join(dir_name, f) for f in listdir(dir_name) if (isfile(join(dir_name, f)) and f.endswith(".jpg"))]
  return onlyfiles


def split_scale_image(input_image, scale_factor):
  r_im, g_im, b_im = input_image.split()
  r_im = ImMath.eval("convert(a, 'F')", a=r_im)
  r_im = ImMath.eval("a * b", a=r_im, b=scale_factor)
  g_im = ImMath.eval("convert(a, 'F')", a=g_im)
  g_im = ImMath.eval("a * b", a=g_im, b=scale_factor)
  b_im = ImMath.eval("convert(a, 'F')", a=b_im)
  b_im = ImMath.eval("a * b", a=b_im, b=scale_factor)
  return r_im, g_im, b_im


def even_image(pil_image):
  width, height = pil_image.size
  if ((width % 2) == 1):
    # crop the width by 1
    pil_image = pil_image.crop((1, 0, width, height))
  if ((height % 2) == 1):
    # crop the height by 1
    pil_image = pil_image.crop((0, 1, width, height))
  return pil_image


def get_image_orientation(pil_image):
  width, height = pil_image.size
  # do a cheap trick to determine orientation
  if (width > height):
    # image is landscape
    image_orientation = LANDSCAPE
  elif (width < height):
    # image is portrait
    image_orientation = PORTRAIT
  elif (width == height):
    # image is square
    image_orientation = SQUARE
  return image_orientation


def pad_image(fname, expand_to):
  this_image = Im.open(fname)
  this_image = even_image(this_image)
  width, height = this_image.size
  image_orientation = get_image_orientation(this_image)
  # this need to find the smallest dim so we can expand that to `expand_to`
  min_dim = min(width, height)
  pad_amount = (expand_to - min_dim) / 2
  # print min_dim + pad_amount + pad_amount
  padded_image = ImOps.expand(
    this_image, border=pad_amount, fill=(255, 255, 255))
  width, height = padded_image.size
  maxDim = max(width, height)
  cropAmount = (maxDim - expand_to) / 2
  if (image_orientation == LANDSCAPE):
    padded_image = padded_image.crop(
      (cropAmount, 0, width - cropAmount, height))
  elif (image_orientation == PORTRAIT):
    padded_image = padded_image.crop(
      (0, cropAmount, width, height - cropAmount))
  elif (image_orientation == SQUARE):
    # don't think I need to do anything here.
    pass
  return padded_image


def square_image(fname, crop_to):
  this_image = Im.open(fname)
  this_image = even_image(this_image)
  width, height = this_image.size
  # this need to find the smallest dim so we can expand that to `expand_to`
  w_crop_amount = (width - crop_to) / 2
  h_crop_amount = (height - crop_to) / 2
  squared_image = this_image.crop(
    (w_crop_amount, h_crop_amount, width - w_crop_amount, 
    height - h_crop_amount))
  sqSzw, sqSzh = squared_image.size
  return squared_image


def print_status(curr_fname, curr_image, total_images):
  print "processing " + curr_fname + " (" + str(curr_image) + " of " + str(
    total_images) + ")"

def get_final_dimension(comb_method, image_widths, image_heights):
  if (comb_method == PAD):
    max_w = max(image_widths)
    max_h = max(image_heights)
    expand_to = max(max_w, max_h)
    if ((expand_to % 2) == 1):
      expand_to -= 1
    return expand_to
  elif (comb_method == CROP):
    min_w = min(image_widths)
    min_h = min(image_heights)
    crop_to = min(min_w, min_h)
    if ((crop_to % 2) == 1):
      crop_to -= 1
    return crop_to
  else: 
    raise ValueError('invalid value for combination_method')

def pad_or_crop(comb_method, fname, output_dimension):
  if (comb_method == PAD):
    pil_image = pad_image(fname, output_dimension)
  elif (comb_method == CROP):
    pil_image = square_image(fname, output_dimension)
  else:
    raise ValueError('invalid value for combination_method')
  return pil_image

def average_dir(imgPath,combination_method,outName):
  # okay, let's get a list of phoots
  phoot_list = get_phoot_list(imgPath)

  # init some vars to store exposure time, etc.
  exposure_times = []
  image_widths = []
  image_heights = []
  total_shutter_open = 0

  # now loop through the list and get exposure times and max dimensions
  for fname in phoot_list:
    this_exposure = get_exposure_time_in_s(fname)
    exposure_times.append(this_exposure)
    total_shutter_open += this_exposure
    # open the image and get the dimensions
    this_im = Im.open(fname)
    width, height = this_im.size
    image_widths.append(width)
    image_heights.append(height)

  # now that we have the total length, calculate scale factors---
  # trying to get as close to what would be an actual multiple exposure
  # as possible
  scale_factors = []
  for exp_time in exposure_times:
    scale_factors.append(exp_time / total_shutter_open)

  output_dimension = get_final_dimension(combination_method, image_widths, image_heights)

  num_images = len(phoot_list)
  fname = phoot_list[0]
  print_status(fname, 1, num_images)
  composite_image = pad_or_crop(combination_method, fname, output_dimension)
  phoot_list.pop(0)
  r_comp_im, g_comp_im, b_comp_im = split_scale_image(composite_image, (1.0 / num_images))

  # now loop through the list again and first expand the images
  # and then combine the images.

  progress_counter = 1
  for fname in phoot_list:
    progress_counter += 1
    print_status(fname, progress_counter, num_images)
    this_image = pad_or_crop(combination_method, fname, output_dimension)
    thisR, thisG, thisB = split_scale_image(this_image, (1.0 / num_images))
    # now add them together
    r_comp_im = ImMath.eval("a + b", a=r_comp_im, b=thisR)
    g_comp_im = ImMath.eval("a + b", a=g_comp_im, b=thisG)
    b_comp_im = ImMath.eval("a + b", a=b_comp_im, b=thisB)

  # (below is what we did before
  # composite_image = Im.blend(composite_image, this_image,0.2)

  # finally convert them back to ints and then merge the image before display.
  r_comp_im = ImMath.eval("convert(a, 'L')", a=r_comp_im)
  g_comp_im = ImMath.eval("convert(a, 'L')", a=g_comp_im)
  b_comp_im = ImMath.eval("convert(a, 'L')", a=b_comp_im)

  # now that everything has been added together, do some histogram equalization
  r_lut = equalize(r_comp_im.histogram())
  g_lut = equalize(g_comp_im.histogram())
  b_lut = equalize(b_comp_im.histogram())

  r_comp_im = r_comp_im.point(r_lut)
  g_comp_im = g_comp_im.point(g_lut)
  b_comp_im = b_comp_im.point(b_lut)

  composite_image = Im.merge('RGB', (r_comp_im, g_comp_im, b_comp_im))

  print "minimum image dimension: " + str(min(min(image_widths),min(image_heights))) + " pixels"
  print "maximum image dimension: " + str(max(max(image_widths), max(image_heights))) + " pixels"
  print "total exposure time in seconds: " + str(total_shutter_open)

  # composite_image.show()
  composite_image.save(outName)

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument("imgPath", help="path of the directory of images you'd like to process")
  parser.add_argument("combination_method", help="either 'crop' (all images are cropped to smallest dimension) or 'pad' (all images are padded to largest dimension))")
  parser.add_argument("outName", help="name of averaged output file including extension")
  args = parser.parse_args()

  average_dir(args.imgPath,args.combination_method,args.outName)