import os

from pathlib import Path

import numpy as np
from skimage import exposure, io

from PIL import Image as Im
from PIL import ImageOps as ImOps
from PIL import ImageMath as ImMath

from photomanip import LANDSCAPE, PORTRAIT, SQUARE, PAD, CROP


class ImageManipulator:
    def __init__(self, *args, **kwargs):
        pass

    def _read_image(self, *args, **kwargs):
        raise NotImplementedError()

    def _even_image(self, *args, **kwargs):
        raise NotImplementedError()

    def _pad_or_crop(self, *args, **kwargs):
        raise NotImplementedError()

    def _pad_image(self, *args, **kwargs):
        raise NotImplementedError()

    def _square_image(self, *args, **kwargs):
        raise NotImplementedError()

    def _get_image_orientation(self, image):
        """Determines the orientation of an image."""
        height, width, _ = image.shape
        # do a cheap trick to determine orientation
        if width > height:
            # image is landscape
            image_orientation = LANDSCAPE
        elif width < height:
            # image is portrait
            image_orientation = PORTRAIT
        elif width == height:
            # image is square
            image_orientation = SQUARE
        return image_orientation

    @staticmethod
    def print_status(curr_fname, curr_image, total_images):
        """Prints the status of the processing run based on input."""
        print("processing {} ({} of {})".format(curr_fname, str(curr_image),
                                                str(total_images)))

    def prepare_image(self, image, comb_method, final_dimension):
        """Ensures an image has even dimensions, determines the images orientation,
         and either pads or crops an image to a specified final dimension."""
        image = self._even_image(image)
        image = self._pad_or_crop(image, comb_method, final_dimension)
        return image

    def split_scale_image(self, image, scale_factor):
        """scales an image by a scale factor band by band."""
        raise NotImplementedError()


class ImageManipulatorSKI(ImageManipulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @staticmethod
    def __ensure_3_dims(image):
        return np.atleast_3d(image)

    def _read_image(self, filename):
        filepath = Path(filename)
        return io.imread(filepath)

    def _even_image(self, image):
        """Ensures an image has even dimensions."""
        image = self.__ensure_3_dims(image)
        height, width, _ = image.shape
        if (width % 2) == 1:
            # crop the width by 1
            image = image[0:, 1:, :]
        if (height % 2) == 1:
            # crop the height by 1
            image = image[1:, 0:, :]
        return image

    def _pad_or_crop(self, image, comb_method, output_dimension):
        """Wrapper function that calls the method to either pad or crop an image based
         on input."""
        if comb_method == PAD:
            image = self._pad_image(image, output_dimension)
        elif comb_method == CROP:
            image = self._square_image(image, output_dimension)
        else:
            raise ValueError('invalid value for combination_method')
        return image

    def _pad_image(self, image, expand_to):
        """Pads an image to a specified dimension."""
        image = self.__ensure_3_dims(image)
        height, width, dim = image.shape
        padded_image = 255 * np.ones((expand_to, expand_to, dim))
        upper_left = (((expand_to - height) // 2),
                      ((expand_to - width) // 2))
        lower_right = ((upper_left[0] + height),
                       (upper_left[1] + width))
        padded_image[upper_left[0]:lower_right[0],
                     upper_left[1]:lower_right[1], :] =\
            image
        return padded_image

    def _square_image(self, image, crop_to):
        """Crops an image to a specified dimension."""
        # this is needed to find the largest dim so we can crop
        # that to `crop_to`
        image = self.__ensure_3_dims(image)
        height, width, _ = image.shape
        w_crop_amount = (width - crop_to) // 2
        h_crop_amount = (height - crop_to) // 2
        square_image = image[
            h_crop_amount:height - h_crop_amount,
            w_crop_amount:width - w_crop_amount,
            :
        ]
        return square_image

    def split_scale_image(self, image, divisor):
        """Divides `image` by a divisor and returns it."""
        return image / divisor

    def combine_images(self,
                       metadata_list: list,
                       output_dimension: int,
                       num_images: int,
                       out_name: Path,
                       combination_method: str = PAD,
                       write_crops: bool = False):
        """Uses OpenCV and associated methods to "average" a list of photographs.
        """
        # preallocate
        composite_image = np.zeros((output_dimension, output_dimension, 3),
                                   dtype=float)

        if write_crops:
            # split off the filename and use that to make a dir
            individual_path = out_name.parent / out_name.stem
            individual_path.mkdir(exist_ok=True)

        # now loop through the images, crop or expand them, and then combine.
        index = 0
        for metadata in metadata_list:
            fname = metadata['SourceFile']
            self.print_status(fname, index + 1, num_images)
            current_image = self._read_image(fname)
            current_image = self.prepare_image(
                current_image,
                combination_method,
                output_dimension
            )
            if write_crops:
                # write out the image before it gets scaled
                io.imsave(str(individual_path / f'{index}.jpg'),
                          current_image.astype('uint8'))
            if "cached" in metadata:
                if metadata["cached"]:
                    scaled_image = current_image
                    index += metadata["num_images"]
                else:
                    scaled_image = self.split_scale_image(
                        current_image,
                        num_images
                    )
                    index += 1
            else:
                scaled_image = self.split_scale_image(
                    current_image,
                    num_images
                )
                index += 1
            composite_image += scaled_image

        composite_float = np.copy(composite_image)
        # Contrast stretching
        data_mask = composite_image != 255
        lower_bound, upper_bound = \
            np.percentile(composite_image[data_mask], (0.5, 99.5))
        composite_image[data_mask] = \
            exposure.rescale_intensity(composite_image[data_mask],
                                       in_range=(lower_bound, upper_bound),
                                       out_range='uint8')

        # write the image
        io.imsave(str(out_name), composite_image.astype('uint8'))
        return composite_float


class ImageManipulatorPIL(ImageManipulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _even_image(self):
        """Ensures an image has even dimensions."""
        if (self.width % 2) == 1:
            # crop the width by 1
            self.this_image = self.this_image.crop(
                (1, 0, self.width, self.height)
                )
            self.width, self.height = self.this_image.size
        if (self.height % 2) == 1:
            # crop the height by 1
            self.this_image = self.this_image.crop(
                (0, 1, self.width, self.height)
                )
            self.width, self.height = self.this_image.size

    def _pad_or_crop(self, comb_method, output_dimension):
        """Wrapper function that calls the method to either pad or crop an image based
         on input."""
        if comb_method == PAD:
            self._pad_image(output_dimension)
        elif comb_method == CROP:
            self._square_image(output_dimension)
        else:
            raise ValueError('invalid value for combination_method')

    def _pad_image(self, expand_to):
        """Pads an image to a specified dimension."""
        # this is needed to find the smallest dim so we can expand
        # that to `expand_to`
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

    def _square_image(self, crop_to):
        """Crops an image to a specified dimension."""
        # this is needed to find the largest dim so we can crop
        # that to `crop_to`
        w_crop_amount = (self.width - crop_to) / 2
        h_crop_amount = (self.height - crop_to) / 2
        self.this_image = self.this_image.crop(
            (w_crop_amount, h_crop_amount, self.width - w_crop_amount,
             self.height - h_crop_amount))

    def _split_scale(self, scale_factor):
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

    def prepare_image(self, comb_method, final_dimension):
        self._get_image_orientation()
        super().prepare_image(comb_method, final_dimension)

    def combine_images_pil(phoot_list, combination_method, output_dimension, out_name):
        """Uses PIL and associated methods to "average" a list of photographs. """
        num_images = len(phoot_list)
        fname = phoot_list[0]
        self.print_status(fname, 1, num_images)
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