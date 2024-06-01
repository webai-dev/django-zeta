from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.shortcuts import redirect
from django.views.defaults import page_not_found, permission_denied
from django.views.generic.base import TemplateView

from graphql_relay.node.node import from_global_id
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from ery_backend.datasets.models import Dataset
from ery_backend.modules.models import ModuleDefinition
from ery_backend.procedures.models import Procedure
from ery_backend.roles.utils import has_privilege, grant_ownership
from ery_backend.stints.models import StintDefinition
from ery_backend.templates.models import Template
from ery_backend.themes.models import Theme
from ery_backend.validators.models import Validator
from ery_backend.widgets.models import Widget

from .serializers import (
    FrontendXMLRenderer,
    LabXMLRenderer,
    ModuleDefinitionXMLRenderer,
    StintDefinitionXMLRenderer,
    TemplateXMLRenderer,
    ThemeXMLRenderer,
    ValidatorXMLRenderer,
    ProcedureXMLRenderer,
    WidgetXMLRenderer,
)


class ExportModelView(LoginRequiredMixin, APIView):
    def get(self, request, gql_id, slugged=False):
        """
        Get serialized xml data.

        Args:
            request (:class:`HttpRequest`): Contains information on current session.
            gql_id (str): The graphql global id used to retrieve instance used for export.
        Returns:
            :class:`HttpResponse`: Response to be sent to client.
        Raises:
            :class:`PermissionDenied`: Trigger when :class:`~ery_backend.users.models.User` does
              not have :class:`~ery_backend.roles.models.Role` assigned having export
              :class:`~ery_backend.roles.models.Privilege` on instance.
            :class:`Http404`: Trigger when model instance to be exported does not exist.
        """
        from rest_framework import serializers

        (_, obj_id) = from_global_id(gql_id)

        try:
            model = self.renderer_classes[0].get_model()
            obj = model.objects.get(pk=int(obj_id))
            if not slugged:
                serializer = obj.get_bxml_serializer()(instance=obj)
            else:
                serializer = type(
                    '{model._meta.object_name}FileExportSerializer',
                    (model.get_bxml_serializer(),),
                    {'slug': serializers.SlugField(required=True, allow_null=False)},
                )
            if has_privilege(obj, request.user, 'export'):
                data = serializer(instance=obj).data
                response = Response(data, content_type='application/ery+xml')
                response['Content-Disposition'] = 'attachment; filename=%s.bxml' % (obj.name,)
                return response
            return permission_denied(request, PermissionDenied())
        except ObjectDoesNotExist:
            return page_not_found(request, ObjectDoesNotExist())


class ExportFrontendView(ExportModelView):
    """
    Implementation of :class:`ExportModelView` for :class:`~ery_backend.frontend.models.Frontend`.
    """

    renderer_classes = (FrontendXMLRenderer,)


class ExportLabView(ExportModelView):
    """
    Implementation of :class:`ExportModelView` for :class:`~ery_backend.labs.models.Lab`.
    """

    renderer_classes = (LabXMLRenderer,)


class ExportModuleDefinitionView(ExportModelView):
    """
    Implementation of :class:`ExportModelView` for :class:`~ery_backend.modules.models.ModuleDefinition`.
    """

    renderer_classes = (ModuleDefinitionXMLRenderer,)


class ExportStintDefinitionView(ExportModelView):
    """
    Implementation of :class:`ExportModelView` for :class:`~ery_backend.stints.models.StintDefinition`.

    Include all child :class:`~ery_backend.modules.models.ModuleDefinition` information in serialized data.
    """

    renderer_classes = (StintDefinitionXMLRenderer,)


class ExportSimpleStintDefinitionView(ExportModelView):
    """
    Implementation of :class:`ExportModelView` for :class:`~ery_backend.stints.models.StintDefinition`.

    Exclude all child :class:`~ery_backend.modules.models.ModuleDefinition` information from serialized data.

    """

    renderer_classes = (StintDefinitionXMLRenderer,)

    def get(self, request, gql_id):
        """
        Get serialized xml data.

        Args:
            request (:class:`HttpRequest`): Contains information on current session.
            gql_id (str): The graphql id used to retrieve instance used for export.

        Returns:
            :class:`HttpResponse`: Response to be sent to client.

        Raises:
            :class:`PermissionDenied`: Trigger when :class:`~ery_backend.users.models.User` does
              not have :class:`~ery_backend.roles.models.Role` assigned having export
              :class:`~ery_backend.roles.models.Privilege` on instance.
            :class:`Http404`: Trigger when model instance to be exported does not exist.
        """
        (_, obj_id) = from_global_id(gql_id)

        try:
            obj = self.renderer_classes[0].get_model().objects.get(pk=int(obj_id))
            if has_privilege(obj, request.user, 'export'):
                response = Response(obj.simple_serialize(), content_type='application/bry+xml')
                response['Content-Disposition'] = 'attachment; filename=%s.bxml' % (obj.name,)
                return response
            return permission_denied(request, PermissionDenied())
        except obj.DoesNotExist:
            return page_not_found(request, ObjectDoesNotExist())


class ExportProcedureView(ExportModelView):
    """
    Implementation of :class:`ExportModelView` for :class:`~ery_backend.procedures.models.Procedure`.
    """

    renderer_classes = (ProcedureXMLRenderer,)


class ExportWidgetView(ExportModelView):
    """
    Implementation of :class:`ExportModelView` for :class:`~ery_backend.widgets.models.Widget`.
    """

    renderer_classes = (WidgetXMLRenderer,)


class ExportTemplateView(ExportModelView):
    """
    Implementation of :class:`ExportModelView` for :class:`~ery_backend.templates.models.Template`.
    """

    renderer_classes = (TemplateXMLRenderer,)


class ExportThemeView(ExportModelView):
    """
    Implementation of :class:`ExportModelView` for :class:`~ery_backend.themes.models.Theme`.
    """

    renderer_classes = (ThemeXMLRenderer,)


class ExportValidatorView(ExportModelView):
    """
    Implementation of :class:`ExportModelView` for :class:`~ery_backend.validators.models.Validator`.
    """

    renderer_classes = (ValidatorXMLRenderer,)


class ImportFileView(LoginRequiredMixin, TemplateView):
    """
    Allow user to post an xml file for import into intended model instance.

    Attributes:
        login_url (str): Link to project's login page.
        redirect_field_name (str): Used to name field within view.
    """

    login_url = '/admin/login/'
    redirect_field_name = 'redirect_to'


class ImportView(LoginRequiredMixin, APIView):
    """
    Allow user to post an xml file for import into intended model instance.

    Attributes:
        parser_classes (tuple[django :class:`Parser`]): Required for serialization.
        import_model (:class:`Model`): Model used for instantiation of serialized data.
    """

    parser_classes = (MultiPartParser, FormParser)
    import_model = None

    def post(self, request):
        """
        Create instance from serialialized xml data.

        Args:
            request (:class:`HttpRequest`): Contains file with data used for import.

        Returns:
            :class:`Model`: Module instance from import_model containing deserialized information.
        """
        user = request.user
        if 'file_to_import' in request.FILES:
            obj_name = request.POST['name']
            bxml_file = request.FILES['file_to_import']
            instance = self.import_model.import_instance_from_xml(bxml_file, obj_name)
            if user.my_folder:
                instance.create_link(user.my_folder)
                grant_ownership(instance, user=user)
            return redirect('/')
        return redirect(f'/{self.import_model._meta.model_name}_file?no_file=1')


class SimpleImportView(LoginRequiredMixin, APIView):
    """
    Allow user to post an xml file for import into intended model instance, without the need
    for defining children.

    Attributes:
        parser_classes (tuple[django :class:`Parser`]): Required for serialization.
        import_model (:class:`Model`): Model used for instantiation of serialized data.
    """

    parser_classes = (MultiPartParser, FormParser)
    import_model = None

    def post(self, request):
        """
        Create instance from serialialized xml data.

        Args:
            request (:class:`HttpRequest`): Contains file with data used for import.

        Returns:
            :class:`Model`: Module instance from import_model containing deserialized information.
        """
        user = request.user
        if 'file_to_import' in request.FILES:
            obj_name = request.POST['name']
            bxml_file = request.FILES['file_to_import']
            instance = self.import_model.import_instance_from_xml(bxml_file, obj_name, simple=True)
            if user.my_folder:
                instance.create_link(user.my_folder)
                grant_ownership(instance, user=user)
            return redirect('/')
        return redirect(f'/simple_{self.import_model._meta.model_name}_file?no_file=1')


class ImportWidgetFileView(ImportFileView):
    """
    Allow user to post an xml file for import into :class:`~ery_backend.widgets.models.Widget`.
    """

    template_name = "import_export/import_widget_file.html"


class ImportWidgetView(ImportView):
    """
    Handle conversion of file recieved from :class:`ImportWidgetView` into
    :class:`~ery_backend.widgets.models.Widget` instance.
    """

    import_model = Widget

    def post(self, request):
        """
        Create instance from serialialized xml data.

        Args:
            - request (:class:`HttpRequest`): Contains file with data used for import.

        Returns:
            :class:`Model`: Module instance from import_model containing deserialized information.
        """
        user = request.user
        if 'file_to_import' in request.FILES:
            obj_name = request.POST['name']
            bxml_file = request.FILES['file_to_import']
            instance = self.import_model.import_instance_from_xml(bxml_file, obj_name)
            if user.my_folder:
                instance.create_link(user.my_folder)
                grant_ownership(instance, user=user)
            return redirect('/')
        return redirect(f'/{self.import_model._meta.model_name}_file?no_file=1')


class ImportProcedureFileView(ImportFileView):
    """
    Allow user to post an xml file for import into :class:`~ery_backend.procedures.models.Procedure`.
    """

    template_name = "import_export/import_procedure_file.html"


class ImportProcedureView(ImportView):
    """
    Handle conversion of file recieved from :class:`ImportProcedureView` into
    :class:`~ery_backend.procedures.models.Procedure` instance.
    """

    import_model = Procedure


class ImportModuleDefinitionFileView(ImportFileView):
    """
    Allow user to post an xml file for import into :class:`~ery_backend.modules.models.ModuleDefinition`.
    """

    template_name = "import_export/import_moduledefinition_file.html"


class ImportModuleDefinitionView(ImportView):
    """
    Handle conversion of file recieved from :class:`ImportModuleDefinitionFileView` into
    :class:`~ery_backend.modules.models.ModuleDefinition` instance.
    """

    import_model = ModuleDefinition


class ImportStintDefinitionFileView(ImportFileView):
    """
    Allow user to post an xml file for import into :class:`~ery_backend.stints.models.StintDefinition`.
    """

    template_name = "import_export/import_stintdefinition_file.html"


class ImportSimpleStintDefinitionView(SimpleImportView):
    """
    Handle conversion of file recieved from :class:`ImportStintDefinitionFileView` into
    :class:`~ery_backend.stints.models.StintDefinition` instance without need for defining children.
    """

    import_model = StintDefinition


class ImportStintDefinitionView(ImportView):
    """
    Handle conversion of file recieved from :class:`ImportStintDefinitionFileView` into
    :class:`~ery_backend.stints.models.StintDefinition` instance.
    """

    import_model = StintDefinition


class ImportTemplateFileView(ImportFileView):
    """
    Allow user to post an xml file for import into :class:`~ery_backend.templates.models.Template`.
    """

    template_name = "import_export/import_template_file.html"


class ImportTemplateView(ImportView):
    """
    Handle conversion of file recieved from :class:`ImportTemplateFileView` into
    :class:`~ery_backend.templates.models.Template` instance.
    """

    import_model = Template


class ImportThemeFileView(ImportFileView):
    """
    Allow user to post an xml file for import into :class:`~ery_backend.themes.models.Theme`.
    """

    template_name = "import_export/import_theme_file.html"


class ImportThemeView(ImportView):
    """
    Handle conversion of file recieved from :class:`ImportThemeView` into
    :class:`~ery_backend.themes.models.Theme` instance.
    """

    import_model = Theme


class ImportValidatorFileView(ImportFileView):
    """
    Allow user to post an xml file for import into :class:`~ery_backend.validators.models.Validator`.
    """

    template_name = "import_export/import_validator_file.html"


class ImportValidatorView(ImportView):
    """
    Handle conversion of file recieved from :class:`ImportValidatorView` into
    :class:`~ery_backend.validators.models.Validator` instance.
    """

    import_model = Validator


class ImportDatasetFileView(LoginRequiredMixin, TemplateView):
    """
    Allow user to post an xml file for import into intended model instance.

    Attributes:
        login_url (str): Link to project's login page.
        redirect_field_name (str): Used to name field within view.
    """

    login_url = '/admin/login/'
    redirect_field_name = 'redirect_to'
    template_name = "import_export/import_dataset_file.html"


class ImportDatasetView(LoginRequiredMixin, APIView):
    """
    Handle conversion of file recieved from :class:`ImportDatasetView` into
    :class:`~ery_backend.datasets.models.Dataset` instance.
    """

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        """
        Create instance from csv data.

        Args:
            request (:class:`HttpRequest`): Contains file with data used for import.

        Returns:
            :class:`~ery_backend.datasets.models.Dataset`
        """
        user = request.user
        if 'file_to_import' in request.FILES:
            obj_name = request.POST['name']
            dataset_file = request.FILES['file_to_import']
            instance = Dataset.objects.create_dataset_from_file(obj_name, dataset_file.read())
            if user.my_folder:
                instance.create_link(user.my_folder)
                grant_ownership(instance, user=user)
            return redirect('/')
        return redirect(f'/{self.import_model._meta.model_name}_file?no_file=1')
