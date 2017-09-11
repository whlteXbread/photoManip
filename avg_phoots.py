#! /usr/local/bin/python3
import argparse
import operator
from functools import reduce
from os import listdir
from os.path import isfile, join
from timeit import default_timer as timer

import cv2

from PIL import Image as Im
from PIL import ImageOps as ImOps
from PIL import ImageMath as ImMath
from PIL.ExifTags import TAGS

EXPOSURE_TIME = 'ExposureTime'
LANDSCAPE = 'landscape'
PORTRAIT = 'portrait'
SQUARE = 'square'
PAD = 'pad'
CROP = 'crop'


class ImageTools(object):
    """Loads an image using PIL and calculates exposure time, image width and height,
     prepares an image for further processing, and splits an image into red, green
     and blue channels and scales the output based on a specified scale factor."""
    def __init__(self, fname, library='pil'):
        self.this_image = Im.open(fname)
        self.width, self.height = self.this_image.size
        self._calculate_exposure_time_in_s()
        self.library = library
        # if we'd rather use openCV, replace the PIL version.
        if self.library == 'cv2':
            self.this_image = cv2.imread(fname,cv2.IMREAD_COLOR)


    def _calculate_exposure_time_in_s(self):
        """Reads the EXIF data from the image file and calculates the exposure time
         in seconds."""
        self.exif_data = {}
        info = self.this_image._getexif()
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            self.exif_data[decoded] = value
        self.exposure_time = self.exif_data[EXPOSURE_TIME]
        self.exposure_time_in_s = (float(self.exposure_time[0])) / (float(self.exposure_time[1]))

    def prepare_image(self, comb_method, final_dimension):
        """Ensures an image has even dimensions, determines the images orientation,
         and either pads or crops an image to a specified final dimension."""
        self._get_image_orientation()
        if self.library == 'cv2':
            self._even_image_cv2()
            self._pad_or_crop_cv2(comb_method, final_dimension)
        else:
            self._even_image_pil()
            self._pad_or_crop_pil(comb_method, final_dimension)

    def _even_image_pil(self):
        """Ensures an image has even dimensions."""
        if (self.width % 2) == 1:
            # crop the width by 1
            self.this_image = self.this_image.crop((1, 0, self.width, self.height))
            self.width, self.height = self.this_image.size
        if (self.height % 2) == 1:
            # crop the height by 1
            self.this_image = self.this_image.crop((0, 1, self.width, self.height))
            self.width, self.height = self.this_image.size


    def _even_image_cv2(self):
        """Ensures an image has even dimensions."""
        if (self.width % 2) == 1:
            # crop the width by 1
            self.this_image = self.this_image[0:self.height, 1:self.width]
            self.height, self.width, _ = self.this_image.shape
        if (self.height % 2) == 1:
            # crop the height by 1
            self.this_image = self.this_image[1:self.height, 0:self.width]
            self.height, self.width, _ = self.this_image.shape


    def _get_image_orientation(self):
        """Determines the orientation of an image."""
        # do a cheap trick to determine orientation
        if self.width > self.height:
            # image is landscape
            self.image_orientation = LANDSCAPE
        elif self.width < self.height:
            # image is portrait
            self.image_orientation = PORTRAIT
        elif self.width == self.height:
            # image is square
            self.image_orientation = SQUARE


    def _pad_or_crop_pil(self, comb_method, output_dimension):
        """Wrapper function that calls the method to either pad or crop an image based
         on input."""
        if comb_method == PAD:
            self._pad_image_pil(output_dimension)
        elif comb_method == CROP:
            self._square_image_pil(output_dimension)
        else:
            raise ValueError('invalid value for combination_method')


    def _pad_or_crop_cv2(self, comb_method, output_dimension):
        """Wrapper function that calls the method to either pad or crop an image based
         on input."""
        if comb_method == PAD:
            self._pad_image_cv2(output_dimension)
        elif comb_method == CROP:
            self._square_image_cv2(output_dimension)
        else:
            raise ValueError('invalid value for combination_method')


    def _pad_image_pil(self, expand_to):
        """Pads an image to a specified dimension."""
        # this is needed to find the smallest dim so we can expand that to `expand_to`
        min_dim = min(self.width, self.height)
        pad_amount = (expand_to - min_dim) / 2
        padded_image = ImOps.expand(
            self.this_image, border=pad_amount, fill=(255, 255, 255))
        width, height = padded_image.size
        max_dim = max(width, height)
        crop_amount = (max_dim - expand_to) / 2
        if self.image_orientation == LANDSCAPE:
            self.this_image = padded_image.crop(
                (crop_amount, 0, width - crop_amount, height))
            self.width, self.height = self.this_image.size
        elif self.image_orientation == PORTRAIT:
            self.this_image = padded_image.crop(
                (0, crop_amount, width, height - crop_amount))
            self.width, self.height = self.this_image.size
        elif self.image_orientation == SQUARE:
            # don't think I need to do anything here.
            pass


    def _square_image_pil(self, crop_to):
        """Crops an image to a specified dimension."""
        # this is needed to find the largest dim so we can crop that to `crop_to`
        w_crop_amount = (self.width - crop_to) / 2
        h_crop_amount = (self.height - crop_to) / 2
        self.this_image = self.this_image.crop(
            (w_crop_amount, h_crop_amount, self.width - w_crop_amount,
             self.height - h_crop_amount))


    def _pad_image_cv2(self, expand_to):
        """Pads an image to a specified dimension."""
        # use copyMakeBorder here
        raise ValueError("Padding an image using OpenCV is not supported (yet).")


    def _square_image_cv2(self, crop_to):
        """Crops an image to a specified dimension."""
        # this is needed to find the largest dim so we can crop that to `crop_to`
        w_crop_amount = (self.width - crop_to) // 2
        h_crop_amount = (self.height - crop_to) // 2
        self.this_image = self.this_image[
            h_crop_amount:self.height - h_crop_amount,
            w_crop_amount:self.width - w_crop_amount]


    def _split_scale_pil(self, scale_factor):
        """Splits an image into red, green, and blue channels and scales
         each channel by specified scale factor."""
        r_im, g_im, b_im = self.this_image.split()
        r_im = ImMath.eval("convert(a, 'F')", a=r_im)
        r_im = ImMath.eval("a * b", a=r_im, b=scale_factor)
        g_im = ImMath.eval("convert(a, 'F')", a=g_im)
        g_im = ImMath.eval("a * b", a=g_im, b=scale_factor)
        b_im = ImMath.eval("convert(a, 'F')", a=b_im)
        b_im = ImMath.eval("a * b", a=b_im, b=scale_factor)
        return r_im, g_im, b_im


    def _split_scale_cv2(self, divisor):
        """Divides `self.this_image` by a divisor and returns it."""
        # actually i am not sure how much sense it makes to do the averaging
        # in the HSV color space.
        return self.this_image / divisor


    def split_scale_image(self, scale_factor):
        """Delegates splitting and scaling responsibility to the appropriate
        method."""
        if self.library == 'cv2':
            return self._split_scale_cv2(scale_factor)
        else:
            return self._split_scale_pil(scale_factor)


# code sample from http://effbot.org/zone/pil-histogram-equalization.htm -------
def equalize(h):
    """Applies histogram equalization to a seficied histogram."""
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


def get_phoot_list(dir_name):
    """Gets a list of files with extension ".jpg" in a folder."""
    onlyfiles = [join(dir_name, f) for f in listdir(dir_name)
                 if isfile(join(dir_name, f)) and f.endswith(".jpg")]
    return onlyfiles

def print_status(curr_fname, curr_image, total_images):
    """Prints the status of the processing run based on input."""
    print("processing {} ({} of {})".format(curr_fname, str(curr_image),
                                            str(total_images)))


def get_final_dimension(comb_method, image_widths, image_heights):
    """Computes the dimensions of the final output image based on specified
     combination method and lists of images widths and heights."""
    if comb_method == PAD:
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


def combine_images_pil(phoot_list, combination_method, output_dimension, out_name):
    """Uses PIL and associated methods to "average" a list of photographs. """
    num_images = len(phoot_list)
    fname = phoot_list[0]
    print_status(fname, 1, num_images)
    current_image = ImageTools(fname, 'pil')
    current_image.prepare_image(combination_method, output_dimension)
    phoot_list.pop(0)
    r_comp_im, g_comp_im, b_comp_im = current_image.split_scale_image((1.0 / num_images))

    # now loop through the list again and first crop or expand the images
    # and then combine them.
    progress_counter = 1
    for fname in phoot_list:
        progress_counter += 1
        print_status(fname, progress_counter, num_images)
        current_image = ImageTools(fname, 'pil')
        current_image.prepare_image(combination_method, output_dimension)
        this_r, this_g, this_b = current_image.split_scale_image((1.0 / num_images))
        # now add them together
        r_comp_im = ImMath.eval("a + b", a=r_comp_im, b=this_r)
        g_comp_im = ImMath.eval("a + b", a=g_comp_im, b=this_g)
        b_comp_im = ImMath.eval("a + b", a=b_comp_im, b=this_b)

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

    # composite_image.show()
    composite_image.save(out_name)

def combine_images_cv2(phoot_list, combination_method, output_dimension, out_name):
    """Uses OpenCV and associated methods to "average" a list of photographs. """
    num_images = len(phoot_list)
    fname = phoot_list[0]
    print_status(fname, 1, num_images)
    current_image = ImageTools(fname, 'cv2')
    current_image.prepare_image(combination_method, output_dimension)
    phoot_list.pop(0)

    composite_image = current_image.split_scale_image(num_images)

    # now loop through the images, crop or expand them, and then combine.
    progress_counter = 1
    for fname in phoot_list:
        progress_counter += 1
        print_status(fname, progress_counter, num_images)
        current_image = ImageTools(fname, 'cv2')
        current_image.prepare_image(combination_method, output_dimension)
        scaled_image = current_image.split_scale_image(num_images)
        composite_image += scaled_image

    # various strategies for histogram equalization follow.
    # TODO: split these out into different functions so it's possible to access
    # all of them.
    # hsv_image = cv2.cvtColor(composite_image.astype('uint8'), cv2.COLOR_BGR2HSV)
    # hsv_image[:, :, 2] = cv2.equalizeHist(hsv_image[:, :, 2])
    # equalized_image = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2BGR)

    # hls_image = cv2.cvtColor(composite_image.astype('uint8'), cv2.COLOR_BGR2HLS)
    # hls_image[:, :, 1] = cv2.equalizeHist(hls_image[:, :, 1])
    # equalized_image = cv2.cvtColor(hls_image, cv2.COLOR_HLS2BGR)

    # equalized_image = composite_image.astype('uint8')
    # clahe = cv2.createCLAHE()
    # equalized_image[:, :, 0] = clahe.apply(equalized_image[:, :, 0])
    # equalized_image[:, :, 1] = clahe.apply(equalized_image[:, :, 1])
    # equalized_image[:, :, 2] = clahe.apply(equalized_image[:, :, 2])

    equalized_image = composite_image.astype('uint8')
    equalized_image[:, :, 0] = cv2.equalizeHist(equalized_image[:, :, 0])
    equalized_image[:, :, 1] = cv2.equalizeHist(equalized_image[:, :, 1])
    equalized_image[:, :, 2] = cv2.equalizeHist(equalized_image[:, :, 2])
    cv2.imwrite(out_name, equalized_image)

def average_dir(img_path, combination_method, out_name, library):
    """Averages, or makes a multiple exposure of all the photos in a specified
     directory."""
    # okay, let's get a list of phoots
    phoot_list = get_phoot_list(img_path)

    # init some vars to store exposure time, etc.
    exposure_times = []
    image_widths = []
    image_heights = []
    total_shutter_open = 0

    # now loop through the list of files and get exposure times and max dimensions
    for fname in phoot_list:
        current_image = ImageTools(fname, 'pil')
        this_exposure = current_image.exposure_time_in_s
        exposure_times.append(this_exposure)
        total_shutter_open += this_exposure
        # get the dimensions
        width, height = current_image.width, current_image.height
        image_widths.append(width)
        image_heights.append(height)

    # now that we have the total length, calculate scale factors---
    # depending on how you think about making a multiple exposure, scaling by
    # the total amount of time the shutter was open is the correct way to go.
    # this time around, though, we'll just approach it more like an average.
    # scale_factors = []
    # for exp_time in exposure_times:
    #     scale_factors.append(exp_time / total_shutter_open)

    output_dimension = get_final_dimension(combination_method, image_widths, image_heights)

    start = timer()
    if library == 'cv2':
        print("using opencv for image processing")
        combine_images_cv2(phoot_list, combination_method, output_dimension, out_name)
    elif library == 'pil':
        print("using pil for image processing")
        combine_images_pil(phoot_list, combination_method, output_dimension, out_name)
    end = timer()

    print("minimum image dimension: {} pixels".format(str(min(min(image_widths),
                                                              min(image_heights)))))
    print("maximum image dimension: {} pixels".format(str(max(max(image_widths),
                                                              max(image_heights)))))
    print("total exposure time in seconds: {}".format(str(total_shutter_open)))
    print("processing time in seconds: {}".format(end - start))


def main():
    """Main function to parse commandline arguments and start the averaginge function."""
    parser = argparse.ArgumentParser()
    parser.add_argument("img_path", help="path of the directory of images you'd like to process")
    parser.add_argument("combination_method",
                        help="""either 'crop' (all images are cropped to smallest dimension) \
                                or 'pad' (all images are padded to largest dimension))""")
    parser.add_argument("out_name", help="name of averaged output file including extension")
    parser.add_argument("library", help="specify which image library to use—either 'cv2' or 'pil'")
    args = parser.parse_args()

    if args.library and (args.library == "cv2"):
        average_dir(args.img_path, args.combination_method, args.out_name,
                    args.library)
    elif args.library and (args.library == "pil"):
        average_dir(args.img_path, args.combination_method, args.out_name,
                    args.library)
    elif not args.library:
        print("No imaging library specified, using PIL.")
        average_dir(args.img_path, args.combination_method, args.out_name,
                    "pil")
    else:
        raise ValueError("{} is not a valid imaging library. Choose either 'pil' or 'cv2'"
                         .format(args.library))

if __name__ == "__main__":
    main()
