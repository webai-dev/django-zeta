import binascii

from django.http import HttpResponse, Http404
from django.shortcuts import redirect

from google_auth_oauthlib.flow import Flow
from graphql_relay import from_global_id

from .models import Dataset


def render_as_csv(request, dataset_id):
    try:
        contenttype, pk = from_global_id(dataset_id)

        if contenttype != "DatasetNode":
            raise ValueError("Invalid indentifer")

        dataset = Dataset.objects.get(pk=pk)
    except (Dataset.DoesNotExist, binascii.Error, ValueError):
        raise Http404("Dataset does not exist")

    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = f"attachment; filename={dataset.name}.csv"
    response.write(dataset.to_pandas().to_csv())

    return response


def _get_flow():
    return Flow.from_client_secrets_file(
        'config/client_secret.json',
        scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/userinfo.email',
            'openid',
            'https://www.googleapis.com/auth/userinfo.profile',
        ],
        redirect_uri='http://localhost:8000/datasets/gsheet_callback',
    )


def render_as_gsheet(request, dataset_id):
    flow = _get_flow()

    auth_url, _ = flow.authorization_url(prompt='consent')
    request.session['gsheet_dataset_id'] = dataset_id

    return redirect(auth_url)


def gsheet_callback(request):
    dataset_id = request.session['gsheet_dataset_id']
    try:
        contenttype, pk = from_global_id(dataset_id)

        if contenttype != "DatasetNode":
            raise ValueError("Invalid indentifer")

        dataset = Dataset.objects.get(pk=pk)
    except (Dataset.DoesNotExist, binascii.Error, ValueError):
        raise Http404("Dataset does not exist")

    flow = _get_flow()
    flow.fetch_token(code=request.GET["code"])

    dataset_gsheet_url = dataset.to_gsheet(flow.credentials)
    return redirect(dataset_gsheet_url)
