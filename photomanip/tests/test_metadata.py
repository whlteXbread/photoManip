import os

from shutil import copyfile

from photomanip.metadata import ImageExif, SetExifTool

from nose import tools

ORIGINAL_IMAGE_FILENAME = 'photomanip/tests/turd_ferguson.jpeg'
TEST_IMAGE_FILENAME = 'photomanip/tests/image_exif_test.jpg'
ORIGINAL_PHOTO_FILENAME = 'photomanip/tests/test_photo_0.jpg'
TEST_PHOTO_01_FILENAME = 'photomanip/tests/image_exposure_test_01.jpg'
TEST_PHOTO_02_FILENAME = 'photomanip/tests/image_exposure_test_02.jpg'


class TestImageExif:
    @classmethod
    def setup_class(cls):
        cls.image_exif = ImageExif()
        copyfile(ORIGINAL_IMAGE_FILENAME, TEST_IMAGE_FILENAME)
        copyfile(ORIGINAL_PHOTO_FILENAME, TEST_PHOTO_01_FILENAME)
        copyfile(ORIGINAL_PHOTO_FILENAME, TEST_PHOTO_02_FILENAME)

    @classmethod
    def teardown_class(cls):
        os.remove(TEST_IMAGE_FILENAME)
        os.remove(TEST_PHOTO_01_FILENAME)
        os.remove(TEST_PHOTO_02_FILENAME)

    def get_stored_tags(self, tag_list, filename):
        with SetExifTool() as et:
            stored_tags = et.get_tags(tag_list, filename)
        return stored_tags

    def test_imageexif_generate_tag_list(self):
        get_list = self.image_exif.get_list
        # test get list
        tag_list = self.image_exif._generate_tag_list(get_list)
        tools.eq_(set(tag_list), set([
            'EXIF:DateTimeOriginal',
            'File:ImageHeight',
            'IPTC:Keywords',
            'EXIF:ExposureTime',
            'File:ImageWidth']))

        # test set list
        tag_list = self.image_exif._generate_tag_list(get_list, True)
        tools.eq_(tag_list, {
            'date_created': 'EXIF:DateTimeOriginal={}',
            'exposure_time': 'EXIF:ExposureTime={}',
            'image_height': 'File:ImageHeight={}',
            'image_width': 'File:ImageWidth={}',
            'keywords': 'IPTC:Keywords={}'})

    def test_set_image_metadata(self):
        output_meta = {
            "name": "Terd Ferguson",
            "keywords": "one, two, three",
            "caption": "suck it, trebeck",
        }
        result = self.image_exif.set_image_metadata(TEST_IMAGE_FILENAME,
                                                    output_meta)
        tools.eq_(result, '1 image files updated\n')
        check_tags = self.image_exif._generate_tag_list(output_meta.keys())
        stored_tags = self.get_stored_tags(check_tags, TEST_IMAGE_FILENAME)
        # now check if the metadata matches
        for key, val in output_meta.items():
            mapped_key = self.image_exif.metadata_map[key]
            tools.eq_(val, stored_tags[mapped_key])

    def test_calculate_exposure_time(self):
        tag_list = self.image_exif._generate_tag_list(['exposure_time'])
        stored_tags = self.get_stored_tags(tag_list, TEST_PHOTO_01_FILENAME)
        tools.eq_(stored_tags['EXIF:ExposureTime'], 0.001333333333)

    def test_get_tags_containing(self):
        tag_list = self.image_exif._generate_tag_list(['keywords'])
        stored_tags = self.get_stored_tags(tag_list, TEST_PHOTO_01_FILENAME)
        result = self.image_exif.get_tags_containing(
            stored_tags['IPTC:Keywords'], 'faceit365')
        tools.eq_(result, 'faceit365:date=20190308')

    def test_get_metadata_batch(self):
        fname_list = [TEST_PHOTO_01_FILENAME, TEST_PHOTO_02_FILENAME]
        meta_list = self.image_exif.get_metadata_batch(fname_list)
        meta_list[0].pop('SourceFile')
        meta_list[1].pop('SourceFile')
        tools.eq_(meta_list[0], meta_list[1])
