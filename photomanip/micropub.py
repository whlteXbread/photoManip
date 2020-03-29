"""inspired by micropub dot py from https://github.com/cleverdevil/ditchbook"""

from datetime import datetime
from pytz import timezone, utc
import requests
import sys


class MicropubAPI:
    def __init__(self, config):
        self.config = config
        self.timezone = timezone(self.config["timezone"])
        self.headers = self._generate_headers()

    @staticmethod
    def _check_operation_success(response):
        if response.status_code == 202:
            return True
        else:
            return False

    def _apply_timezone(self, dt, default=utc):
        return self.timezone.localize(dt).astimezone(default)

    def _generate_headers(self):
        headers = {
            "Authorization": f"Bearer {self.config['token']}",
        }
        if "mp_destination" in self.config:
            headers["mp-destination"] = self.config["mp_destination"]
        return headers

    def _upload(self, file_path):
        print("Attempting to upload:", file_path)

        with open(file_path, "rb") as image_fp:
            files = {"file": ("image.jpg", image_fp, "image/jpeg")}
            response = requests.post(
                self.config["mp_media_endpoint"],
                headers=self.headers,
                files=files
            )

        if self._check_operation_success(response):
            print("  Uploaded -> ", response.headers["Location"])
            return response.headers["Location"]
        else:
            print("  Failed to upload! Status code", response.status_code)
            sys.exit(1)
            return None

    def _publish(self, mf2):
        response = requests.post(
            self.config['mp_endpoint'],
            json=mf2,
            headers=self.headers
        )

        if self._check_operation_success(response):
            print("  Published -> ", response.headers["Location"])
            return response.headers["Location"]
        else:
            print("  Failed to publish! Status code", response.status_code)
            print("  error:", response.text)
            sys.exit(1)
            return None

    def process_post(self, post_text, image_file_list, alt_text=None):

        dt = self._apply_timezone(datetime.now())
        # create MF2 container
        mf2 = {
            "type": ["h-entry"],
            "properties": {
                "published": [dt.isoformat(sep=" ")]
            }
        }

        # upload photos, if any
        photos = []
        for index, photo in enumerate(image_file_list):
            if alt_text:
                if isinstance(alt_text, list):
                    alternate = alt_text[index]
                elif isinstance(alt_text, str):
                    alternate = alt_text
                photos.append({
                    "value": self._upload(photo),
                    "alt": alternate
                })
            else:
                photos.append(self._upload(photo))
        if len(photos):
            mf2["properties"]["photo"] = photos

        # prepare content
        if len(post_text):
            mf2["properties"]["content"] = [post_text]

        # publish it
        self._publish(mf2)
