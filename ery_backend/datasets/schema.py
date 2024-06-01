import graphene
from graphql_relay import to_global_id
from graphql_relay.node.node import from_global_id

from ery_backend.datastore.ery_client import get_datastore_client
from ery_backend.base.schema import PrivilegedNodeMixin
from ery_backend.base.schema_utils import EryObjectType
from ery_backend.roles.utils import has_privilege
from ery_backend.users.utils import authenticated_user

from .models import Dataset


class DatasetRow(graphene.ObjectType):
    def __init__(self, row_id, columns, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = row_id
        self.columns = columns

    id = graphene.Field(graphene.ID)
    columns = graphene.List(graphene.String)

    @staticmethod
    def get(dataset_id, index):
        """Get the contents of a row from the google datastore

        Args:
            dataset_id: :class:~/ery_backend.datasets.models.Dataset.pk The dataset pk identifier
            index: int Numeric index of the row

        Returns:
            DatastRow
        """
        client = get_datastore_client()
        dataset_slug = Dataset.objects.filter(id=dataset_id).values_list('slug', flat=True).first()
        dataset_key = client.key("dataset", dataset_slug)
        dataset = client.get(dataset_key)

        if dataset is None:
            raise ValueError("Failed to retrieve datasets for {}".format(dataset_key))

        key = client.key("row", index, parent=dataset_key)
        entity = client.get(key)

        row_id = "{}:{}".format(dataset_id, index)
        columns = [entity.get(h, None) for h in dataset["headers"]]

        return DatasetRow(row_id, columns)

    def resolve_columns(self, info, *args, **kwargs):
        return self.columns

    def resolve_id(self, info, *args, **kwargs):
        return to_global_id("DatasetRow", self.id)


class DatasetNode(PrivilegedNodeMixin, EryObjectType):
    class Meta:
        model = Dataset

    rows = graphene.List(DatasetRow)

    export_csv = graphene.String()
    export_json = graphene.String()
    export_html = graphene.String()

    def resolve_rows(self, info, *args, **kwargs):  # pylint:disable=no-self-use
        rows = []
        for i in range(len(self.rows)):
            row_id = "{}:{}".format(self.pk, (i + 1))
            # pylint:disable=unsubscriptable-object
            rows.append(DatasetRow(row_id, [self.rows[i][header] for header in self.headers]))
        return rows

    def resolve_export_csv(self, info):
        return self.to_pandas().to_csv()

    def resolve_export_json(self, info):
        return self.to_pandas().to_json()

    def resolve_export_html(self, info):
        return self.to_pandas().to_html()


DefaultDatasetQuery = DatasetNode.get_query_class()


class DatasetQuery(DefaultDatasetQuery):
    dataset_row = graphene.Field(DatasetRow, id=graphene.ID(required=True))

    def resolve_dataset_row(self, info, *args, **kwargs):  # pylint:disable=no-self-use
        user = authenticated_user(info.context)

        _, identifiers = from_global_id(kwargs["id"])
        dataset_id, row_id = identifiers.split(":")

        ds = Dataset.objects.get(pk=dataset_id)

        if has_privilege(ds, user, "read"):
            return DatasetRow.get(int(dataset_id), int(row_id))

        raise ValueError("not authorized")
