import os

from ery_backend.base.testcases import EryTestCase


from ..utils import image_type
from ..models import ImageAsset


TEST_DIR = os.path.dirname(os.path.abspath(__file__))


class TestUtils(EryTestCase):
    """
    Test the utility helpers
    """

    def test_image_type(self):
        """We can detect image types."""

        def right_type(filename, expect):
            path = os.path.join(TEST_DIR, "data", filename)

            with open(path, "rb") as f:
                data = f.read()

            self.assertEqual(image_type(data), expect)

        right_type("ags.gif", ImageAsset.HTTP_CONTENT_TYPES.gif)
        right_type("burger.png", ImageAsset.HTTP_CONTENT_TYPES.png)
        right_type("iamnotacatidontsaymeow.jpg", ImageAsset.HTTP_CONTENT_TYPES.jpeg)

    def test_invalid_type(self):
        """Unsupported image types are unsupported"""

        path = os.path.join(TEST_DIR, "data", "art_of_unix_programming.pdf")

        with open(path, "rb") as f:
            data = f.read()

        self.assertRaises(ValueError, image_type, data)
