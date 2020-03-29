import click
import flickrapi
import webbrowser
import yaml

from photomanip.metadata import ImageExif
from photomanip.micropub import MicropubAPI


class Uploader:
    def __init__(self, config_yaml):
        self.api_keys = self.yaml_file_to_dict(config_yaml)

    def yaml_file_to_dict(self, filename):
        with open(filename) as yaml_file:
            return yaml.load(yaml_file)

    def _upload_file(self, filename):
        raise NotImplementedError()

    def _check_permissions(self):
        raise NotImplementedError()

    def upload(self):
        raise NotImplementedError()


class FlickrUploader(Uploader):
    def __init__(self, config_yaml):
        super().__init__(config_yaml)
        self.api = flickrapi.FlickrAPI(
            self.api_keys["flickr"]["key"],
            self.api_keys["flickr"]["secret"],
            cache=True,
        )
        self._check_permissions()
        self.exif_reader = ImageExif(get_list=["name"])

    def _check_permissions(self):
        if not self.api.token_valid(perms="write"):
            try:
                print(
                    "specified credentials do not have write access. "
                    "attempting to authenticate."
                )
                # Get a request token
                self.api.get_request_token(oauth_callback='oob')

                # Open a browser at the authentication URL.
                authorize_url = self.api.auth_url(perms='write')
                webbrowser.open_new_tab(authorize_url)

                # Get the verifier code from the user.
                verifier = str(input('Verifier code: '))

                # Trade the request token for an access token
                self.api.get_access_token(verifier)

                assert self.api.token_valid(perms="write")
            except Exception as e:
                print(f"unable to gain write permissions: {e}")

    def _check_operation_success(self, result):
        return result.attrib["stat"] == "ok"

    def _upload_file(self, filename):
        # get the photo title, since flickr prefers filename if not specified
        exif_result = self.exif_reader.get_metadata_batch([filename])
        name = exif_result[0][self.exif_reader.metadata_map["name"]]
        result = self.api.upload(filename=filename, title=name)
        if not self._check_operation_success(result):
            raise RuntimeError("unable to upload file")
        # return the photoID of the uploaded file so we can use it
        return result.getchildren()[0].text

    def _add_flickr_photo_to_set(self, photo_id, set_id):
        result = self.api.photosets.addPhoto(
            photoset_id=set_id,
            photo_id=photo_id
        )
        if not self._check_operation_success(result):
            raise RuntimeError(
                f"unable to add photo {photo_id} to set {set_id}"
            )

    def upload(self, filename, set_id):
        photo_id = self._upload_file(filename)
        self._add_flickr_photo_to_set(photo_id, set_id)


class MicropubUploader(Uploader):
    def __init__(self, config_yaml):
        super().__init__(config_yaml)
        self.config = self.api_keys["micropub"]
        self.api = MicropubAPI(self.config)

    def upload(self, post_text, image_file_list):
        self.api.process_post(post_text, image_file_list)
