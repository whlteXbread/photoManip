import os

from pathlib import Path

import numpy as np

from nose import tools

from photomanip import PAD, CROP
from photomanip.grouper import FileSystemGrouper
from photomanip.manipulator import ImageManipulatorCV2


class TestIMCV2:

    @classmethod
    def setup_class(cls):
        cls.fs_grouper = FileSystemGrouper('photomanip/tests/')
        cls.im_cv2 = ImageManipulatorCV2()
        cls.color_test_image = np.ones((111, 131, 3), dtype=np.bool)
        cls.bw_test_image_3 = np.ones((111, 131, 1), dtype=np.bool)
        cls.bw_test_image_1 = np.ones((111, 131), dtype=np.bool)
        cls.cv2_pad_fname = Path('photomanip/tests/year_pad_cv2.jpeg')
        cls.cv2_crop_fname = Path('photomanip/tests/year_crop_cv2.jpeg')

    @classmethod
    def teardown_class(cls):
        os.unlink(cls.cv2_pad_fname)
        os.unlink(cls.cv2_crop_fname)

    def test_even_image(self):
        # color image
        test_image = self.im_cv2._even_image(self.color_test_image)
        tools.eq_(test_image.shape, (110, 130, 3))

        # bw image
        test_image = self.im_cv2._even_image(self.bw_test_image_3)
        tools.eq_(test_image.shape, (110, 130, 1))

        test_image = self.im_cv2._even_image(self.bw_test_image_1)
        tools.eq_(test_image.shape, (110, 130, 1))

    def test_pad_image(self):
        # color image
        test_image = self.im_cv2._pad_image(self.color_test_image, 200)
        tools.eq_(test_image.shape, (200, 200, 3))

        # bw image
        test_image = self.im_cv2._pad_image(self.bw_test_image_3, 200)
        tools.eq_(test_image.shape, (200, 200, 1))

        test_image = self.im_cv2._pad_image(self.bw_test_image_1, 200)
        tools.eq_(test_image.shape, (200, 200, 1))

    def test_square_image(self):
        # color image
        test_image = self.im_cv2._even_image(self.color_test_image)
        test_image = self.im_cv2._square_image(test_image, 100)
        tools.eq_(test_image.shape, (100, 100, 3))

        # bw image
        test_image = self.im_cv2._even_image(self.bw_test_image_3)
        test_image = self.im_cv2._square_image(test_image, 100)
        tools.eq_(test_image.shape, (100, 100, 1))

        test_image = self.im_cv2._even_image(self.bw_test_image_1)
        test_image = self.im_cv2._square_image(test_image, 100)
        tools.eq_(test_image.shape, (100, 100, 1))

    def test_split_scale_image(self):
        # color image
        test_image = self.im_cv2.split_scale_image(
            self.color_test_image * 3,
            3
        )
        tools.eq_(np.any(test_image != 1), False)

        # bw image
        test_image = self.im_cv2.split_scale_image(
            self.bw_test_image_3 * 3,
            3
        )
        tools.eq_(np.any(test_image != 1), False)

        test_image = self.im_cv2.split_scale_image(
            self.bw_test_image_1 * 3,
            3
        )
        tools.eq_(np.any(test_image != 1), False)

    def test_combine_images(self):
        # group by year to test all the images
        meta_list = list(self.fs_grouper.group_by_year().values())[0]

        # test the padding method first
        comb_method = PAD
        common_dimension = self.fs_grouper.get_common_dimension(
            comb_method,
            meta_list
        )
        self.im_cv2.combine_images(
            meta_list,
            common_dimension,
            self.cv2_pad_fname,
            comb_method
        )
        image_result = self.im_cv2._read_image(str(self.cv2_pad_fname))
        tools.eq_(image_result.shape, (200, 200, 3))

        # test the crop method
        comb_method = CROP
        common_dimension = self.fs_grouper.get_common_dimension(
            comb_method,
            meta_list
        )
        self.im_cv2.combine_images(
            meta_list,
            common_dimension,
            self.cv2_crop_fname,
            comb_method
        )
        image_result = self.im_cv2._read_image(str(self.cv2_crop_fname))
        tools.eq_(image_result.shape, (132, 132, 3))
