import logging

from django.contrib.auth import get_user_model

from graphql_jwt.utils import get_payload, get_http_authorization, get_user_by_natural_key
from graphql_jwt.exceptions import JSONWebTokenError

from ery_backend.users.utils import auth0_userinfo

User = get_user_model()

logger = logging.getLogger(__name__)


class JSONWebTokenBackend:
    @staticmethod
    def authenticate(request=None, **credentials):
        if request is None:
            return None
        logger.info("path is '%s'", request.path)
        token = get_http_authorization(request)
        logger.info("bearer token is '%s'", token)
        if token is None:
            token = request.COOKIES.get('behavery_access_token')
            logger.info("access token is '%s'", token)

        if token is not None:
            payload = get_payload(token)
            logger.info("payload is '%s'", payload)
            username = payload.get("sub")

            if not username:
                raise JSONWebTokenError("Invalid payload")

            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                profile = auth0_userinfo(token)
                user = User.objects.create_user(username=username, profile=profile)

            if user is not None and not user.is_active:
                raise JSONWebTokenError("User is disabled")

            return user

        return None

    @staticmethod
    def get_user(user_id):
        return get_user_by_natural_key(user_id)
