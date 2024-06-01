from graphql_relay.node.node import from_global_id

from django.http import Http404

from ery_backend.assets.models import ImageAsset


def download_image_asset(request, gql_id):
    """
    Get content of an :class:`~ery_backend.assets.models.ImageAsset` from Google Cloud Storage.

    Args:
        asset_id (int)

    Returns:
        bytes: Image content.

    Raises:
        - :class:`django.core.exceptions.ObjectDoesNotExist`: Raised if :class:`~ery_backend.assets.models.ImageAsset` does \
          not exist.
    """
    _, django_id = from_global_id(gql_id)
    image = ImageAsset.objects.get(id=django_id)
    try:
        response = image.http_response
    except ValueError:
        raise Http404("Image does not exist")
    return response
