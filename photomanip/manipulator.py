from pathlib import Path

import numpy as np
from skimage import exposure, io, transform

from photomanip import LANDSCAPE, PORTRAIT, SQUARE, PAD, CROP, RESIZE


class ImageManipulator:
    def __init__(self, *args, **kwargs):
        pass

    def _read_image(self, *args, **kwargs):
        raise NotImplementedError()

    def _even_image(self, *args, **kwargs):
        raise NotImplementedError()

    def _prepare_image(self, *args, **kwargs):
        raise NotImplementedError()

    def _pad_image(self, *args, **kwargs):
        raise NotImplementedError()

    def _square_image(self, *args, **kwargs):
        raise NotImplementedError()

    def _resize_image(self, *args, **kwargs):
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
        image = self._prepare_image(image, comb_method, final_dimension)
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

    @staticmethod
    def _calculate_resize_dimensions(height, width, resize_to):

        # np ftw
        image_size = np.array([height, width])

        # find min and max dimensions, and their locations
        min_dim = np.min(image_size)
        min_ind = np.argmin(image_size)
        max_dim = np.max(image_size)
        max_ind = np.argmax(image_size)

        # calculate aspect ratio
        aspect_ratio = max_dim / min_dim

        # calculate new size
        new_min_dim = resize_to
        new_max_dim = int(round(resize_to * aspect_ratio))

        # store new size
        image_size[min_ind] = new_min_dim
        image_size[max_ind] = new_max_dim

        # you did it
        return tuple(image_size)

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

    def _prepare_image(self, image, comb_method, output_dimension):
        """Wrapper function that calls the method to either pad or crop an image based
         on input."""
        combination_methods = {
            PAD: self._pad_image,
            CROP: self._square_image,
            RESIZE: self._resize_image,
        }
        comb_method = combination_methods[comb_method]

        return comb_method(image, output_dimension)

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

    def _resize_image(self, image, resize_to):
        # resizes image to requested dimension
        image = self.__ensure_3_dims(image)
        height, width, depth = image.shape

        # figure out if we are upscaling or downscaling
        # if downscaling, do anti_aliasing
        max_dim = max(height, width)
        downscaling = max_dim > resize_to

        # calculate output dimensions
        new_height, new_width = self._calculate_resize_dimensions(
            height,
            width,
            resize_to
        )

        # resize the image, unless somehow they're exactly equal
        if height == new_height or width == new_width:
            new_image = self._even_image(image)
        else:
            new_image = transform.resize(
                image,
                (new_height, new_width, depth),
                preserve_range=True,
                anti_aliasing=downscaling
            )
            new_image = self._even_image(new_image)

        return self._square_image(new_image, resize_to)

    def split_scale_image(self, image, divisor):
        """Divides `image` by a divisor and returns it."""
        return image / divisor

    def combine_images(self,
                       metadata_list: list,
                       output_dimension: int,
                       num_images: int,
                       out_name: Path,
                       combination_method: str = RESIZE,
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
