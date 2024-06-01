from urllib.request import urlopen, Request
import json

from django.conf import settings
from django.contrib.auth import get_user_model

from jose import jwt
from graphql_jwt.settings import jwt_settings
from graphql_jwt.exceptions import JSONWebTokenError

User = get_user_model()


def auth0_userinfo(token):
    req = Request(
        "https://{}/userinfo".format(settings.AUTH0_DOMAIN),
        headers={
            "Authorization": "{} {}".format(jwt_settings.JWT_AUTH_HEADER_PREFIX, token),
            "Content-type": "application/json",
        },
    )
    jsonurl = urlopen(req)
    userinfo = json.loads(jsonurl.read())

    return userinfo


def jwt_payload(user, context=None):
    pass


def jwt_decode(token, context=None):
    jsonurl = urlopen("https://{}/.well-known/jwks.json".format(settings.AUTH0_DOMAIN))
    jwks = json.loads(jsonurl.read())
    unverified_header = jwt.get_unverified_header(token)

    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {"kty": key["kty"], "kid": key["kid"], "use": key["use"], "n": key["n"], "e": key["e"]}
    if not rsa_key:
        raise JSONWebTokenError("Unable to find appropriate key")

    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=[jwt_settings.JWT_ALGORITHM],
            audience=jwt_settings.JWT_AUDIENCE,
            issuer=jwt_settings.JWT_ISSUER,
        )
    except jwt.ExpiredSignatureError:
        raise JSONWebTokenError("Token is expired")
    except jwt.JWTClaimsError:
        raise JSONWebTokenError("Incorrect claims, please check the audience and issuer")
    except Exception:
        raise JSONWebTokenError("Unable to parse authentication token.")

    return payload


def authenticated_user(context):
    """Takes a DJango request context.  Returns the user if the context contains
    an authenticated user, raises ValueError otherwise.
    """

    if hasattr(context, "get"):
        user = context.get("user", None)
    else:
        user = getattr(context, "user", None)

    if user is None or not user.is_authenticated:
        raise ValueError("not authorized")

    return user
