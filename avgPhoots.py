#! /usr/bin/python
from PIL import Image as Im
from PIL import ImageOps as ImOps
from PIL import ImageMath as ImMath
from PIL.ExifTags import TAGS
from os import listdir
from os.path import isfile, join
import argparse
import operator

# code sample from http://effbot.org/zone/pil-histogram-equalization.htm -------
def equalize(h):
  lut = []
  for b in range(0, len(h), 256):
    # step size
    step = reduce(operator.add, h[b:b+256]) / 255
    # create equalization lookup table
    n = 0
    for i in range(256):
      lut.append(n / step)
      n = n + h[i+b]
  return lut
# code sample from http://effbot.org/zone/pil-histogram-equalization.htm -------

def get_exposure_time_in_s(fn):
    ret = {}
    i = Im.open(fn)
    info = i._getexif()
    for tag, value in info.items():
        decoded = TAGS.get(tag, tag)
        ret[decoded] = value
    exposureTime = ret['ExposureTime']
    exposureTimeinS = (float(exposureTime[0])) / (float(exposureTime[1]))
    return exposureTimeinS

def get_phoot_list(dirName):
  onlyfiles = [join(dirName,f) for f in listdir(dirName) if (isfile(join(dirName, f)) and f.endswith(".jpg"))]
  return onlyfiles

def split_scale_image(inImage,numImages):
  rIm, gIm, bIm = inImage.split()
  rIm = ImMath.eval("a / b",a=rIm,b=numImages)
  gIm = ImMath.eval("a / b",a=gIm,b=numImages)
  bIm = ImMath.eval("a / b",a=bIm,b=numImages)
  return rIm, gIm, bIm

def even_image(pilImage):
  thisImW, thisImH = pilImage.size
  if ((thisImW % 2) == 1):
    # crop the width by 1
    pilImage = pilImage.crop((1,0,thisImW,thisImH))
  if ((thisImH % 2) == 1):
    # crop the height by 1
    pilImage = pilImage.crop((0,1,thisImW,thisImH))
  return pilImage

def get_image_orientation(pilImage):
  thisImW, thisImH = pilImage.size
  # do a cheap trick to determine orientation
  if (thisImW > thisImH):
    # image is landscape
    thisImOrient = 'landscape'
  elif (thisImW < thisImH):
    # image is portrait
    thisImOrient = 'portrait'
  elif (thisImW == thisImH):
    # image is square
    thisImOrient = 'square'
  return thisImOrient

def pad_image(fname,expandTo):
  thisImage = Im.open(fname)
  thisImage = even_image(thisImage)
  thisImW, thisImH = thisImage.size
  thisImOrient = get_image_orientation(thisImage)
  # this need to find the smallest dim so we can expand that to `expandTo`
  minDim = min(thisImW,thisImH)
  padAmount = (expandTo - minDim) / 2
  #print minDim + padAmount + padAmount
  
  paddedImage = ImOps.expand(thisImage,border=padAmount,fill=(255,255,255))
  compImW, compImH = paddedImage.size
  maxDim = max(compImW,compImH)
  cropAmount = (maxDim - expandTo) / 2
  if (thisImOrient == 'landscape'):
    paddedImage = paddedImage.crop((cropAmount,0,compImW - cropAmount,compImH))
  elif (thisImOrient == 'portrait'):
    paddedImage = paddedImage.crop((0,cropAmount,compImW,compImH - cropAmount))
  elif (thisImOrient == 'square'):
    # don't think I need to do anything here.
    pass
  return paddedImage

def square_image(fname,cropTo):
  thisImage = Im.open(fname)
  thisImage = even_image(thisImage)
  thisImW, thisImH = thisImage.size
  thisImOrient = get_image_orientation(thisImage)
  # this need to find the smallest dim so we can expand that to `expandTo`
  wCropAmount = (thisImW - cropTo) / 2
  hCropAmount = (thisImH - cropTo) / 2
  
  squaredImage = thisImage.crop((wCropAmount,hCropAmount,thisImW - wCropAmount,thisImH - hCropAmount))
  sqSzw, sqSzh = squaredImage.size
  return squaredImage

def print_status(currImage,totalImages):
  print "processing " + phootList[0] + " (" + str(currImage) + " of " + str(totalImages) + ")"

def pad_or_crop(combMethod,fname):
  if (combMethod == "pad"):
    pilImage = pad_image(fname, expandTo)
  elif (combMethod == "crop"):
    pilImage = square_image(fname, cropTo)
  else:
    raise ValueError('invalid value for combinationMethod')
  return pilImage

if __name__ == "__main__": 
  parser = argparse.ArgumentParser()
  parser.add_argument("imgPath", help="path of the directory of images you'd like to process")
  parser.add_argument("combinationMethod", help="either 'crop' (all images are cropped to smallest dimension) or 'pad' (all images are padded to largest dimension))")
  parser.add_argument("outName", help="name of averaged output file including extension")
  args = parser.parse_args()

  # okay, let's get a list of phoots
  phootList = get_phoot_list(args.imgPath)

  # init some vars to store exposure time, etc.
  exposureTimes = []
  imageWs = []
  imageHs = []
  totalShutterOpen = 0

  # now loop through the list and get exposure times and max dimensions
  for fname in phootList:
    thisExposure = get_exposure_time_in_s(fname)
    exposureTimes.append(thisExposure)
    totalShutterOpen += thisExposure
    # open the image and get the dimensions
    thisIm = Im.open(fname)
    thisImW, thisImH = thisIm.size
    imageWs.append(thisImW)
    imageHs.append(thisImH)

  maxW = max(imageWs)
  maxH = max(imageHs)
  minW = min(imageWs)
  minH = min(imageHs)

  expandTo = max(maxW,maxH)
  if ((expandTo % 2) == 1):
    expandTo -= 1
  cropTo = min(minW,minH)
  if ((cropTo % 2) == 1):
    cropTo -= 1

  numImages = len(phootList)
  print_status(1, numImages)
  fname = phootList[0]
  compositeImage = pad_or_crop(args.combinationMethod, fname)
  phootList.pop(0)
  rCompIm, gCompIm, bCompIm = split_scale_image(compositeImage, numImages)

  # now loop through the list again and first expand the images
  # and then combine the images.

  progressCounter = 1
  for fname in phootList:
    progressCounter += 1
    print_status(progressCounter, numImages)
    thisImage = pad_or_crop(args.combinationMethod,fname)
    thisR, thisG, thisB = split_scale_image(thisImage, numImages)
    # now add them together
    rCompIm = ImMath.eval("a + b",a=rCompIm,b=thisR)
    gCompIm = ImMath.eval("a + b",a=gCompIm,b=thisG)
    bCompIm = ImMath.eval("a + b",a=bCompIm,b=thisB)
  
    # (below is what we did before
    #compositeImage = Im.blend(compositeImage,thisImage,0.2)
  
  # finally convert them back to ints and then merge the image before display.
  rCompIm = ImMath.eval("convert(a, 'L')",a=rCompIm)
  gCompIm = ImMath.eval("convert(a, 'L')",a=gCompIm)
  bCompIm = ImMath.eval("convert(a, 'L')",a=bCompIm)
  
  # now that everything has been added together, do some histogram equalization
  rLut = equalize(rCompIm.histogram())
  gLut = equalize(gCompIm.histogram())
  bLut = equalize(bCompIm.histogram())
  
  rCompIm = rCompIm.point(rLut)
  gCompIm = gCompIm.point(gLut)
  bCompIm = bCompIm.point(bLut)
  compositeImage = Im.merge('RGB',(rCompIm,gCompIm,bCompIm))

  print "minimum image dimension: " + str(cropTo) + " pixels"
  print "maximum image dimension: " + str(expandTo) + " pixels"
  print "total exposure time in seconds: " + str(totalShutterOpen)

  # compositeImage.show()
  compositeImage.save(args.outName)