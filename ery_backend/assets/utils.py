import imghdr

from .models import ImageAsset


def image_type(data):
    name = imghdr.what("", data)

    if name is None:
        raise ValueError("not an image")

    try:
        result = getattr(ImageAsset.HTTP_CONTENT_TYPES, name)
    except AttributeError:
        raise ValueError("unsupported image type")

    return result
