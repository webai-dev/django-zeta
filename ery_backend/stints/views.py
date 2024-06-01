import csv
import logging

from graphql_relay import from_global_id
import numpy

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, Http404
from django.shortcuts import render, redirect

from ery_backend.datastore.entities import csv_fields
from ery_backend.frontends.models import Frontend
from ery_backend.hands.models import Hand
from ery_backend.stint_specifications.models import StintSpecification
from ery_backend.vendors.models import Vendor

from .models import Stint

logger = logging.getLogger(__name__)


@login_required
def render_stint(request, stint_gql_id):
    try:
        stint = Stint.objects.get_by_gql_id(stint_gql_id)
        hand = Hand.objects.get(user=request.user, stint=stint)
    except Hand.DoesNotExist:
        raise Http404("Stint does not exist")
    except ValueError as err:
        return HttpResponseBadRequest(str(err))

    # XXX: Needs removal of load tag, which is not included in Jinja env
    # if not stint.active:
    #     return render(request, 'stints/wait.html')

    hand.frontend = Frontend.objects.get(name='Web')
    hand.save()

    render_code = hand.stint.render(hand)
    return HttpResponse(render_code)


@login_required
def render_datastore_csv(request, stint_gql_id):
    """Produce a CSV of the stint's variables, as they were saved in the datastore"""

    try:
        stint = Stint.objects.get_by_gql_id(stint_gql_id)
    except Stint.DoesNotExist:
        raise Http404("Stint does not exist")

    #   XXX: Temporarily disabled
    #   FIXME !!
    #    user = request.user
    #    if not has_privilege(stint, user, "read_data"):
    #        return HttpResponseForbidden("not authorized")

    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = f"attachment;filename=data_{stint_gql_id}.csv"
    headers = csv_fields + stint.variable_names()
    response.write(",".join(headers))
    response.write("\n")
    dataset = stint.to_dataset(save=False)
    dataset_row = dataset.rows[0]
    rows = []
    for dataset_row in dataset.rows:
        output = {}
        for header in headers:
            value = dataset_row[header] if header in dataset_row else ''
            output[header] = value
        rows.append(output)
    csv_out = csv.DictWriter(response, headers, dialect="unix")
    for row in rows:
        csv_out.writerow(row)

    return response


def render_lenns_csv(request, stint_gql_id):
    """
    Produce a lenns specific CSV of the stint's variables, as they were saved in the datastore.

    Lenns Specific:
        - Return msot recent row per hand/household member
        - Return most recent row per hand/custom dnm
    """

    def convert_nan_to_none(value):
        if isinstance(value, (numpy.float64, numpy.float)) and numpy.isnan(value):
            return None
        return value

    try:
        stint = Stint.objects.get_by_gql_id(stint_gql_id)
    except Stint.DoesNotExist:
        raise Http404("Stint does not exist")
    #   XXX: Temporarily disabled
    #   FIXME !!
    # user = request.user
    # if not has_privilege(stint, user, "read_data"):
    #     return HttpResponseForbidden("not authorized")

    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = f"attachment;filename=data_{stint_gql_id}.csv"
    headers = csv_fields + stint.variable_names()
    response.write(",".join(headers))
    response.write("\n")
    dataset = stint.to_dataset(save=False)
    df = dataset.to_pandas()
    hh_member_rows = []
    custom_dnm_rows = []
    # If user has written to datastore for this stint
    if all([key in df.columns for key in ['run_started', 'hand_id', 'hh_member_id', 'hh_id']]):
        hh_member_groups = (
            df.sort_values(by='run_started', ascending=False).groupby(['hand_id', 'hh_member_id', 'hh_id']).head(1)
        )
        is_real_member = hh_member_groups['hh_member_id'] >= 1
        hh_member_row_count = hh_member_groups[is_real_member]['hh_member_id'].count()
        for i in range(hh_member_row_count):
            row_dict = hh_member_groups[is_real_member].iloc[i][[*headers]].to_dict()
            cleaned_row_dict = {k: convert_nan_to_none(v) for k, v in row_dict.items()}
            hh_member_rows.append(cleaned_row_dict)
    if all([key in df.columns for key in ['run_started', 'custom_dnm_id', 'hh_id']]):
        custom_dnm_groups = (
            df.sort_values(by='run_started', ascending=False).groupby(['custom_dnm_id', 'hand_id', 'hh_id']).head(1)
        )
        is_real_dnm = custom_dnm_groups['custom_dnm_id'] >= 1
        custom_dnm_row_count = custom_dnm_groups[is_real_dnm]['custom_dnm_id'].count()
        for i in range(custom_dnm_row_count):
            row_dict = custom_dnm_groups[is_real_dnm].iloc[i][[*headers]].to_dict()
            cleaned_row_dict = {k: convert_nan_to_none(v) for k, v in row_dict.items()}
            custom_dnm_rows.append(cleaned_row_dict)

    csv_out = csv.DictWriter(response, headers, dialect="unix")
    for row in hh_member_rows + custom_dnm_rows:
        csv_out.writerow(row)

    return response


def output_entity_vars(csv_out, base_data, entities):
    """
    Output the csv data derived from base_data combined with each entity.yield_csv_vars()

    Args:
        csv_out: a fully prepared :class:`css.writer`
        base_data: a dict of prepared fields to be included with every row
        entities: list of objects carrying the :class:`~ery_backend.datastore.core.CsvMixin` (WriteEntity, TeamEntity, or
        HandEntity)
    """
    for entity in entities:
        variables = entity.yield_csv_vars()

        for variable in variables:
            csv_out.writerow({**base_data, **entity.csv_data, **variable})


# XXX: Address in issue #511. Remove once a real view is built for stint page.
@login_required
def test_stint_view(request, stint_gql_id):
    return render(request, 'stints/test_cover.html/', {'stint_gql_id': stint_gql_id})


def redirect_to_market_stint(request, started_by_gql_id=None, frontend_name='Web'):
    from ery_backend.users.backends import JSONWebTokenBackend
    from django.contrib.auth import login

    if not request.user.is_authenticated:
        token_user = JSONWebTokenBackend.authenticate(request)

        if token_user:
            login(request, token_user, backend='django.contrib.auth.backends.ModelBackend')
        else:
            redirect_url = f'{settings.LOGIN_URL}?next={request.build_absolute_uri()}'
            if started_by_gql_id:
                redirect_url += f'/started_by/{started_by_gql_id}'
            return redirect(redirect_url)

    logger.info("User is '%s'", request.user.username if request.user else 'Unknown')

    vendor = Vendor.get_vendor_by_request(request)
    frontend = Frontend.objects.get(name=frontend_name)

    market_stints = Stint.objects.filter(
        status=Stint.STATUS_CHOICES.running,
        stint_specification__where_to_run=StintSpecification.WHERE_TO_RUN_CHOICES.market,
        stint_specification__vendor=vendor,
    )

    if started_by_gql_id:
        _, started_by_id = from_global_id(started_by_gql_id)
        market_stints = market_stints.filter(started_by__id=started_by_id)

    hand = None
    active_stints = market_stints.filter(hands__user=request.user)
    if active_stints.exists():
        # User hasn't completed stint once already
        most_recent_stint = active_stints.order_by('-started').first()
        hand = most_recent_stint.hands.get(user=request.user)
        if not active_stints.filter(hands__status=Hand.STATUS_CHOICES.active).exists():
            most_recent_stint.reset_hand(hand, frontend)
    else:
        most_recent_stint = market_stints.order_by('-started').first()
        if most_recent_stint:
            hand = most_recent_stint.join_user(request.user, frontend)

    if not most_recent_stint:
        raise Http404(f"There are no running marketplace stints for user with id: {started_by_gql_id}")

    if not hand:
        raise Http404(f"Unable to join the stint with current hand.")

    return redirect(f"/stints/{most_recent_stint.gql_id}")


def test_spa(request):
    import os

    file_address = f'{os.getcwd()}/react-spa/es5/bundle.html'
    with open(file_address, 'rb') as f:
        response = HttpResponse(content=f.read())
    return response
