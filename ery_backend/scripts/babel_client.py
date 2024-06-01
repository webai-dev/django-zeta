import grpc

from django.conf import settings

from .grpc.babel_pb2 import ES6Code, ES6CodeBundle
from .grpc.babel_pb2_grpc import BabelStub


def convert_es6_code(code):
    channel = grpc.insecure_channel(settings.ERY_BABEL_HOSTPORT)
    stub = BabelStub(channel)
    es6code = ES6Code(code=code)
    return stub.Convert(es6code)


def convert_es6_bundle(bundle):
    channel = grpc.insecure_channel(settings.ERY_BABEL_HOSTPORT)
    stub = BabelStub(channel)

    es6code = ES6CodeBundle(bundle=[ES6Code(name=name, code=code) for name, code in bundle.items()])
    return stub.ConvertBundle(es6code)


if __name__ == '__main__':
    import sys

    convert_es6_code(sys.argv[1])
