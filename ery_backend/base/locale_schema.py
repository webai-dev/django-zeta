from languages_plus.models import Language
from countries_plus.models import Country

from ery_backend.base.schema_utils import EryObjectType


class LanguageNode(EryObjectType):
    class Meta:
        model = Language
        use_dataloader = False


LanguageQuery = LanguageNode.get_query_class()


class CountryNode(EryObjectType):
    class Meta:
        model = Country
        use_dataloader = False


CountryQuery = CountryNode.get_query_class()
