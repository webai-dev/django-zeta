# pylint: disable=too-many-lines

import json
import random

import graphene
from graphql_relay.node.node import from_global_id
from languages_plus.models import Language

from ery_backend.base.testcases import GQLTestCase, random_dt_value
from ery_backend.base.utils import get_gql_id
from ery_backend.conditions.factories import ConditionFactory
from ery_backend.modules.factories import ModuleDefinitionFactory
from ery_backend.modules.schema import ModuleDefinitionQuery
from ery_backend.mutations import (
    FormMutation,
    FormItemMutation,
    FormButtonListMutation,
    FormButtonMutation,
    FormFieldChoiceMutation,
    FormFieldChoiceTranslationMutation,
    FormFieldMutation,
)
from ery_backend.roles.utils import grant_role
from ery_backend.variables.factories import VariableDefinitionFactory
from ery_backend.variables.models import VariableDefinition
from ery_backend.validators.factories import ValidatorFactory
from ery_backend.widgets.factories import WidgetFactory

from ..factories import (
    FormFactory,
    FormItemFactory,
    FormFieldFactory,
    FormButtonListFactory,
    FormButtonFactory,
    FormFieldChoiceFactory,
    FormFieldChoiceTranslationFactory,
)
from ..models import Form, FormItem, FormButtonList, FormField, FormButton, FormFieldChoice, FormFieldChoiceTranslation
from ..schema import (
    FormQuery,
    FormItemQuery,
    FormFieldQuery,
    FormButtonListQuery,
    FormButtonQuery,
    FormFieldChoiceQuery,
    FormFieldChoiceTranslationQuery,
)


class TestQuery(
    FormQuery,
    ModuleDefinitionQuery,
    FormItemQuery,
    FormFieldQuery,
    FormButtonListQuery,
    FormButtonQuery,
    FormFieldChoiceQuery,
    FormFieldChoiceTranslationQuery,
    graphene.ObjectType,
):
    pass


class TestMutation(
    FormMutation,
    FormItemMutation,
    FormFieldMutation,
    FormButtonListMutation,
    FormButtonMutation,
    FormFieldChoiceMutation,
    FormFieldChoiceTranslationMutation,
    graphene.ObjectType,
):
    pass


class TestReadForm(GQLTestCase):
    node_name = "FormNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def test_read_requires_login(self):
        form = FormFactory()

        td = {"gqlId": form.gql_id}

        query = """query Form($gqlId: ID!){form(id: $gqlId){name comment}}"""
        result = self.gql_client.execute(query, variable_values=td)
        self.assert_query_was_unauthorized(result)

        query = """{allForms {edges {node{name comment moduleDefinition{id name}}}}}"""
        result = self.gql_client.execute(query)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        forms = [FormFactory(), FormFactory(), FormFactory()]

        for form in forms:
            grant_role(self.viewer["role"], form.get_privilege_ancestor(), self.viewer["user"])

        for form in forms[1:]:
            grant_role(self.editor["role"], form.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], forms[2].get_privilege_ancestor(), self.owner["user"])

        query = """{allForms {edges {node {id name comment moduleDefinition{id name}}}}}"""

        # Viewer
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allForms"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allForms"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allForms"]["edges"]), 1)


class TestCreateForm(GQLTestCase):
    node_name = "FormNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.md = ModuleDefinitionFactory()

        self.td = {"mdId": self.md.gql_id, "name": "TestCreateRequiresPrivileges", "comment": "not this one"}

        self.query = """
mutation CreateForm($mdId: ID!, $name: String, $comment: String) {
    createForm(input: {
        moduleDefinition: $mdId,
        name: $name,
        comment: $comment
    }) {
        formEdge {
            node {
                id
                name
                comment
                moduleDefinition{ name }
            }
        }
    }
}
                """

    def test_create_requires_privileges(self):
        grant_role(self.viewer["role"], self.md, self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_create_produces_form(self):
        grant_role(self.owner["role"], self.md, self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertEqual(result["data"]["createForm"]["formEdge"]["node"]["moduleDefinition"]["name"], self.md.name)

        self.td.pop("mdId")

        for field in self.td:
            self.assertEqual(
                result["data"]["createForm"]["formEdge"]["node"][field], self.td[field], msg=f"mismatch on {field}"
            )

        lookup = Form.objects.get(name=self.td["name"])

        self.assertEqual(lookup.module_definition, self.md)

        for field in self.td:
            self.assertEqual(getattr(lookup, field, None), self.td[field], msg=f"mismatch on {field}")


class TestUpdateForm(GQLTestCase):
    node_name = "FormNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form = FormFactory()
        self.td = {
            "name": "TestUpdateRequiresPrivilege",
            "comment": "Allow this change",
            "formId": self.form.gql_id,
        }
        self.query = """mutation UpdateForm($formId: ID!, $name: String, $comment: String)
                    { updateForm( input: {
                        id: $formId,
                        name: $name,
                        comment: $comment})
                    {form{  id name comment moduleDefinition { id }}}}
                """

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.form.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.form.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.td.pop('formId')
        self.form.refresh_from_db()

        for field in self.td:
            self.assertEqual(result["data"]["updateForm"]["form"][field], self.td[field], msg=f"mismatch on {field}")

        for field in self.td:
            self.assertEqual(getattr(self.form, field, None), self.td[field], msg=f"mismatch on {field}")


class TestDeleteForm(GQLTestCase):
    node_name = "FormNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form = FormFactory()
        self.td = {"gqlId": self.form.gql_id}
        self.query = """mutation DeleteForm($gqlId: ID!){ deleteForm(input: {id: $gqlId}){id}}"""

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.form.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        Form.objects.get(pk=self.form.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.form.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteForm"]["id"])
        self.assertRaises(Form.DoesNotExist, Form.objects.get, **{"pk": self.form.id})


class TestReadFormItem(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        form_item = FormItemFactory()
        self.td = {"gqlId": form_item.gql_id}
        self.form_query = """
query FormItem($gqlId: ID!){
    formItem(id: $gqlId){
        order
        tabOrder
        form{id name}
        buttonList{id}
        field{id}
    }
}"""
        self.all_query = """{allFormItems {edges {node{order tabOrder form{id name} buttonList{id} field{id}}}}}"""

    def test_read_requires_login(self):
        result = self.gql_client.execute(self.form_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(self.form_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        form_items = [FormItemFactory(), FormItemFactory(), FormItemFactory()]

        for form_item in form_items:
            grant_role(self.viewer["role"], form_item.get_privilege_ancestor(), self.viewer["user"])

        for form_item in form_items[1:]:
            grant_role(self.editor["role"], form_item.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], form_items[2].get_privilege_ancestor(), self.owner["user"])

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormItems"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormItems"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormItems"]["edges"]), 1)


class TestCreateFormItem(GQLTestCase):
    node_name = "FormItemNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form = FormFactory()

        self.td = {"formId": self.form.gql_id, "order": 2, "tabOrder": 1}

        self.query = """
mutation CreateFormItem($formId: ID!, $order: Int, $tabOrder: Int) {
    createFormItem(input: {
        form: $formId,
        order: $order,
        tabOrder: $tabOrder
    }) {
        formItemEdge {
            node {
                id
                form {id name}
                field {id}
                buttonList {id}
                order
                tabOrder
            }
        }
    }
}
                """

    def test_create_requires_privileges(self):
        grant_role(self.viewer["role"], self.form.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_create_produces_formitem(self):
        grant_role(self.owner["role"], self.form.get_privilege_ancestor(), self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)
        self.assertEqual(result["data"]["createFormItem"]["formItemEdge"]["node"]["form"]["name"], self.form.name)

        self.td.pop("formId")
        tab_order = self.td.pop("tabOrder")
        form_item_gql_id = result["data"]["createFormItem"]["formItemEdge"]["node"]["id"]
        for field in self.td:
            self.assertEqual(
                result["data"]["createFormItem"]["formItemEdge"]["node"][field], self.td[field], msg=f"mismatch on {field}"
            )

        lookup = FormItem.objects.get(id=from_global_id(form_item_gql_id)[1])

        self.assertEqual(lookup.form, self.form)

        self.assertEqual(lookup.tab_order, tab_order)


class TestUpdateFormItem(GQLTestCase):
    node_name = "FormItemNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        form = FormFactory()
        self.form_item = FormItemFactory(form=form, child_type=False)
        FormFieldFactory(form_item=self.form_item)  # Auto adds field to form_item as well
        self.td = {"formItemId": self.form_item.gql_id, "tabOrder": 2}
        self.query = """mutation UpdateFormItem($formItemId: ID!, $tabOrder: Int)
                    { updateFormItem( input: {
                        id: $formItemId,
                        tabOrder: $tabOrder})
                    {formItem{  id field {id} buttonList {id} tabOrder }}}
                """

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.form_item.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.form_item.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.form_item.refresh_from_db()
        self.assertEqual(result["data"]["updateFormItem"]["formItem"]["tabOrder"], 2)


class TestDeleteFormItem(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form_item = FormItemFactory()
        self.td = {"gqlId": self.form_item.gql_id}
        self.query = """mutation DeleteFormItem($gqlId: ID!){ deleteFormItem(input: {id: $gqlId}){id}}"""

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.form_item.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        FormItem.objects.get(pk=self.form_item.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.form_item.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteFormItem"]["id"])
        self.assertRaises(FormItem.DoesNotExist, FormItem.objects.get, **{"pk": self.form_item.id})


class TestReadFormField(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        form_field = FormFieldFactory()
        self.td = {"gqlId": form_field.gql_id}
        self.form_field_query = """
query FormField($gqlId: ID!){
    formField(id: $gqlId){
        formItem {id}
        widget {id}
        randomMode
        variableDefinition {id}
        validator {id}
        disable {id}
        initialValue
        helperText
        required
    }
}"""
        self.all_query = """
{
    allFormFields{
        edges{
            node{
                formItem {id}
                widget {id}
                randomMode
                variableDefinition {id}
                validator {id}
                disable {id}
                initialValue
                helperText
                required
            }
        }
    }
}"""

    def test_read_requires_login(self):
        result = self.gql_client.execute(self.form_field_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(self.form_field_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        form_fields = [FormFieldFactory(), FormFieldFactory(), FormFieldFactory()]

        for form_field in form_fields:
            grant_role(self.viewer["role"], form_field.get_privilege_ancestor(), self.viewer["user"])

        for form_field in form_fields[1:]:
            grant_role(self.editor["role"], form_field.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], form_fields[2].get_privilege_ancestor(), self.owner["user"])

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormFields"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormFields"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormFields"]["edges"]), 1)


class TestCreateFormField(GQLTestCase):
    node_name = "FormFieldNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form = FormFactory()
        self.form_item = FormItemFactory(form=self.form, child_type=False)

        forbidden_choices = [
            VariableDefinition.DATA_TYPE_CHOICES.stage,
            VariableDefinition.DATA_TYPE_CHOICES.list,
            VariableDefinition.DATA_TYPE_CHOICES.dict,
        ]
        self.variable_definition = VariableDefinitionFactory(
            module_definition=self.form.module_definition,
            data_type=random.choice(
                [data_type for data_type, _ in VariableDefinition.DATA_TYPE_CHOICES if data_type not in forbidden_choices]
            ),
        )
        self.validator = ValidatorFactory(code=None)
        self.disable = ConditionFactory(module_definition=self.form.module_definition)
        self.widget = WidgetFactory()
        self.td = {
            "name": "DatsMe",
            "formItemId": self.form_item.gql_id,
            "widget": self.widget.gql_id,
            "randomMode": random.choice([choice for choice, _ in FormField.RANDOM_CHOICES]),
            "variableDefinition": self.variable_definition.gql_id,
            "validator": self.validator.gql_id,
            "disable": self.disable.gql_id,
            "initialValue": json.dumps(random_dt_value(self.variable_definition.data_type)),
            "helperText": "Do what it says",
            "required": random.choice([True, False]),
        }

        self.query = """
mutation CreateFormField(
    $formItemId: ID!,
    $name: String!,
    $widget: ID!,
    $randomMode: String,
    $variableDefinition: ID!,
    $validator: ID,
    $disable: ID,
    $initialValue: JSONString,
    $helperText: String,
    $required: Boolean) {
    createFormField(input: {
        name: $name,
        formItem: $formItemId,
        widget: $widget,
        randomMode: $randomMode,
        variableDefinition: $variableDefinition,
        validator: $validator,
        disable: $disable,
        initialValue: $initialValue,
        helperText: $helperText,
        required: $required
    }) {
        formFieldEdge {
            node {
                id
                name
                formItem {id}
                widget {id}
                randomMode
                variableDefinition {id}
                validator {id}
                disable {id}
                initialValue
                helperText
                required
            }
        }
    }
}
"""

    def test_create_requires_privileges(self):
        grant_role(self.viewer["role"], self.form.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_create_produces_formfield(self):
        grant_role(self.owner["role"], self.form.get_privilege_ancestor(), self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.td.pop("formItemId")
        self.assertEqual(self.form_item.gql_id, result["data"]["createFormField"]["formFieldEdge"]["node"]["formItem"]["id"])
        self.td.pop("widget")
        self.assertEqual(self.widget.gql_id, result["data"]["createFormField"]["formFieldEdge"]["node"]["widget"]["id"])
        self.td.pop("variableDefinition")
        self.assertEqual(
            self.variable_definition.gql_id,
            result["data"]["createFormField"]["formFieldEdge"]["node"]["variableDefinition"]["id"],
        )
        self.td.pop("validator")
        self.assertEqual(self.validator.gql_id, result["data"]["createFormField"]["formFieldEdge"]["node"]["validator"]["id"])
        self.td.pop("disable")
        self.assertEqual(self.disable.gql_id, result["data"]["createFormField"]["formFieldEdge"]["node"]["disable"]["id"])

        for field in self.td:
            result_value = result["data"]["createFormField"]["formFieldEdge"]["node"][field]
            td_value = self.td[field]
            if isinstance(result_value, str):  # Due to returned values from enum fields
                result_value = result_value.lower()
                td_value = td_value.lower()
            self.assertEqual(result_value, td_value, msg=f"mismatch on {field}")

        lookup = FormField.objects.get(id=from_global_id(result["data"]["createFormField"]["formFieldEdge"]["node"]["id"])[1])

        self.assertEqual(lookup.form_item, self.form_item)


class TestUpdateFormField(GQLTestCase):
    node_name = "FormFieldNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form_field = FormFieldFactory()
        module_definition = self.form_field.get_privilege_ancestor()
        self.variable_definition = VariableDefinitionFactory(module_definition=module_definition)
        self.validator = ValidatorFactory(code=None)
        self.disable = ConditionFactory(module_definition=module_definition)
        self.td = {
            "variableDefinition": self.variable_definition.gql_id,
            "validator": self.validator.gql_id,
            "disable": self.disable.gql_id,
            "formFieldId": self.form_field.gql_id,
        }
        self.query = """mutation UpdateFormField($variableDefinition: ID, $validator: ID, $disable: ID, $formFieldId: ID!)
                    { updateFormField( input: {
                        id: $formFieldId,
                        variableDefinition: $variableDefinition,
                        validator: $validator
                        disable: $disable
                    })
                    {formField{  id variableDefinition {id} validator {id} disable {id} }}}
                """

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.form_field.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.form_field.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertEqual(
            result["data"]["updateFormField"]["formField"]["variableDefinition"]["id"], self.variable_definition.gql_id
        )
        self.assertEqual(result["data"]["updateFormField"]["formField"]["validator"]["id"], self.validator.gql_id)
        self.assertEqual(result["data"]["updateFormField"]["formField"]["disable"]["id"], self.disable.gql_id)


class TestDeleteFormField(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form_field = FormFieldFactory()
        self.td = {"gqlId": self.form_field.gql_id}
        self.query = """mutation DeleteFormField($gqlId: ID!){ deleteFormField(input: {id: $gqlId}){id}}"""

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.form_field.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        FormField.objects.get(pk=self.form_field.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.form_field.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteFormField"]["id"])
        self.assertRaises(FormField.DoesNotExist, FormField.objects.get, **{"pk": self.form_field.id})


class TestReadFormButtonList(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        form_button_list = FormButtonListFactory()
        self.td = {"gqlId": form_button_list.gql_id}
        self.form_button_list_query = """
query FormButtonList($gqlId: ID!){
    formButtonList(id: $gqlId){
        formItem {id}
        name
        comment
    }
}"""
        self.all_query = """
{
    allFormButtonLists{
        edges{
            node{
                formItem {id}
                name
                comment
            }
        }
    }
}"""

    def test_read_requires_login(self):
        result = self.gql_client.execute(self.form_button_list_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(self.form_button_list_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        form_button_lists = [FormButtonListFactory(), FormButtonListFactory(), FormButtonListFactory()]

        for form_button_list in form_button_lists:
            grant_role(self.viewer["role"], form_button_list.get_privilege_ancestor(), self.viewer["user"])

        for form_button_list in form_button_lists[1:]:
            grant_role(self.editor["role"], form_button_list.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], form_button_lists[2].get_privilege_ancestor(), self.owner["user"])

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormButtonLists"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormButtonLists"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormButtonLists"]["edges"]), 1)


class TestCreateFormButtonList(GQLTestCase):
    node_name = "FormButtonListNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form_item = FormItemFactory(child_type=False)

        self.td = {
            "name": "DatsMe",
            "formItemId": self.form_item.gql_id,
        }

        self.query = """
mutation CreateFormButtonList($formItemId: ID!, $name: String!){
    createFormButtonList(input: {
        name: $name,
        formItem: $formItemId,
    }) {
        formButtonListEdge {
            node {
                id
                name
                formItem {id}
            }
        }
    }
}
"""

    def test_create_requires_privileges(self):
        grant_role(self.viewer["role"], self.form_item.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_create_produces_buttonlist(self):
        grant_role(self.owner["role"], self.form_item.get_privilege_ancestor(), self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.td.pop("formItemId")
        self.assertEqual(
            self.form_item.gql_id, result["data"]["createFormButtonList"]["formButtonListEdge"]["node"]["formItem"]["id"]
        )

        for field in self.td:
            result_value = result["data"]["createFormButtonList"]["formButtonListEdge"]["node"][field]
            td_value = self.td[field]
            if isinstance(result_value, str):  # Due to returned values from enum fields
                result_value = result_value.lower()
                td_value = td_value.lower()
            self.assertEqual(result_value, td_value, msg=f"mismatch on {field}")

        lookup = FormButtonList.objects.get(
            id=from_global_id(result["data"]["createFormButtonList"]["formButtonListEdge"]["node"]["id"])[1]
        )

        self.assertEqual(lookup.form_item, self.form_item)


class TestUpdateFormButtonList(GQLTestCase):
    node_name = "FormButtonListNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form_button_list = FormButtonListFactory(add_buttons=True)
        self.td = {"name": "NewListWhoDist?", "formButtonListId": self.form_button_list.gql_id}
        self.query = """mutation UpdateFormButtonList($name: String, $formButtonListId: ID!){
                    updateFormButtonList( input: {
                        id: $formButtonListId,
                        name: $name
                    })
                    {formButtonList{  id name buttons{ edges{ node{ id }}} }}}
                """

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.form_button_list.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.form_button_list.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)
        self.assertEqual(result["data"]["updateFormButtonList"]["formButtonList"]["name"], self.td['name'])


class TestDeleteFormButtonList(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form_button_list = FormButtonListFactory()
        self.td = {"gqlId": self.form_button_list.gql_id}
        self.query = """mutation DeleteFormButtonList($gqlId: ID!){ deleteFormButtonList(input: {id: $gqlId}){id}}"""

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.form_button_list.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        FormButtonList.objects.get(pk=self.form_button_list.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.form_button_list.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteFormButtonList"]["id"])
        self.assertRaises(FormButtonList.DoesNotExist, FormButtonList.objects.get, **{"pk": self.form_button_list.id})


class TestReadFormButton(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        form_button = FormButtonFactory()
        self.td = {"gqlId": form_button.gql_id}
        self.form_button_query = """
query FormButton($gqlId: ID!){
    formButton(id: $gqlId){
        buttonList {id}
        widget {id}
        submit
        disable {id}
        hide {id}
    }
}"""
        self.all_query = """
{
    allFormButtons{
        edges{
            node{
                buttonList {id}
                widget {id}
                submit
                disable {id}
                hide {id}
            }
        }
    }
}"""

    def test_read_requires_login(self):
        result = self.gql_client.execute(self.form_button_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(self.form_button_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        form_buttons = [FormButtonFactory(), FormButtonFactory(), FormButtonFactory()]

        for form_button in form_buttons:
            grant_role(self.viewer["role"], form_button.get_privilege_ancestor(), self.viewer["user"])

        for form_button in form_buttons[1:]:
            grant_role(self.editor["role"], form_button.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], form_buttons[2].get_privilege_ancestor(), self.owner["user"])

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormButtons"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormButtons"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormButtons"]["edges"]), 1)


class TestCreateFormButton(GQLTestCase):
    node_name = "FormButtonNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.button_list = FormButtonListFactory()
        self.module_definition = self.button_list.get_privilege_ancestor()
        self.widget = WidgetFactory()
        self.disable = ConditionFactory(module_definition=self.module_definition)
        self.hide = ConditionFactory(module_definition=self.module_definition)
        self.td = {
            "name": "DatsMe",
            "widget": self.widget.gql_id,
            "disable": self.disable.gql_id,
            "hide": self.hide.gql_id,
            "buttonList": self.button_list.gql_id,
            "submit": random.choice([True, False]),
        }

        self.query = """
mutation CreateFormButton(
    $name: String!,
    $widget: ID!,
    $disable: ID,
    $hide: ID,
    $buttonList: ID!
    $submit: Boolean,
    ){
    createFormButton(input: {
        name: $name,
        widget: $widget,
        disable: $disable,
        hide: $hide,
        buttonList: $buttonList,
        submit: $submit,
    }){
        formButtonEdge {
            node {
                id
                name
                widget {id}
                disable {id}
                hide {id}
                buttonList {id}
                submit
            }
        }
    }
}
"""

    def test_create_requires_privileges(self):
        grant_role(self.viewer["role"], self.module_definition, self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_create_produces_formbutton(self):
        grant_role(self.owner["role"], self.module_definition, self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.td.pop("widget")
        self.assertEqual(self.widget.gql_id, result["data"]["createFormButton"]["formButtonEdge"]["node"]["widget"]["id"])
        self.td.pop("disable")
        self.assertEqual(self.disable.gql_id, result["data"]["createFormButton"]["formButtonEdge"]["node"]["disable"]["id"])
        self.td.pop("hide")
        self.assertEqual(self.hide.gql_id, result["data"]["createFormButton"]["formButtonEdge"]["node"]["hide"]["id"])
        self.td.pop("buttonList")
        self.assertEqual(
            self.button_list.gql_id, result["data"]["createFormButton"]["formButtonEdge"]["node"]["buttonList"]["id"]
        )

        for field in self.td:
            result_value = result["data"]["createFormButton"]["formButtonEdge"]["node"][field]
            td_value = self.td[field]
            if isinstance(result_value, str):  # Due to returned values from enum fields
                result_value = result_value.lower()
                td_value = td_value.lower()
            self.assertEqual(result_value, td_value, msg=f"mismatch on {field}")

        lookup = FormButton.objects.get(
            id=from_global_id(result["data"]["createFormButton"]["formButtonEdge"]["node"]["id"])[1]
        )

        self.assertEqual(lookup.button_list, self.button_list)


class TestUpdateFormButton(GQLTestCase):
    node_name = "FormButtonNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form_button = FormButtonFactory()
        module_definition = self.form_button.get_privilege_ancestor()
        form = FormFactory(module_definition=module_definition)
        item = FormItemFactory(form=form, child_type=False)
        self.button_list = FormButtonListFactory(form_item=item)
        self.widget = WidgetFactory()
        self.disable = ConditionFactory(module_definition=module_definition)
        self.hide = ConditionFactory(module_definition=module_definition)
        self.td = {
            "widget": self.widget.gql_id,
            "disable": self.disable.gql_id,
            "hide": self.hide.gql_id,
            "buttonList": self.button_list.gql_id,
            "submit": random.choice([True, False]),
            "formButtonId": self.form_button.gql_id,
        }

        self.query = """
mutation UpdateFormButton($widget: ID, $disable: ID, $hide: ID, $buttonList: ID, $submit: Boolean, $formButtonId: ID!){
    updateFormButton( input: {
        id: $formButtonId,
        widget: $widget,
        disable: $disable,
        hide: $hide,
        buttonList: $buttonList,
        submit: $submit
    })
    {formButton{  id widget {id} disable {id} hide {id} buttonList{ id buttons{ edges{ node{ id }}}} submit }}}
"""

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.form_button.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.form_button.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertEqual(result["data"]["updateFormButton"]["formButton"]["widget"]["id"], self.widget.gql_id)
        self.assertEqual(result["data"]["updateFormButton"]["formButton"]["disable"]["id"], self.disable.gql_id)
        self.assertEqual(result["data"]["updateFormButton"]["formButton"]["hide"]["id"], self.hide.gql_id)
        self.assertEqual(result["data"]["updateFormButton"]["formButton"]["buttonList"]["id"], self.button_list.gql_id)
        self.assertEqual(result["data"]["updateFormButton"]["formButton"]["submit"], self.td['submit'])


class TestDeleteFormButton(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form_button = FormButtonFactory()
        self.td = {"gqlId": self.form_button.gql_id}
        self.query = """mutation DeleteFormButton($gqlId: ID!){ deleteFormButton(input: {id: $gqlId}){id}}"""

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.form_button.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        FormButton.objects.get(pk=self.form_button.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.form_button.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteFormButton"]["id"])
        self.assertRaises(FormButton.DoesNotExist, FormButton.objects.get, **{"pk": self.form_button.id})


class TestReadFormFieldChoice(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        form_field_choice = FormFieldChoiceFactory()
        self.td = {"gqlId": form_field_choice.gql_id}
        self.form_field_choice_query = """
query FormFieldChoice($gqlId: ID!){
    formFieldChoice(id: $gqlId){
        field {id}
        value
        order
    }
}"""
        self.all_query = """
{
    allFormFieldChoices{
        edges{
            node{
                field {id}
                value
                order
            }
        }
    }
}"""

    def test_read_requires_login(self):
        result = self.gql_client.execute(self.form_field_choice_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(self.form_field_choice_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        form_field_choices = [FormFieldChoiceFactory(), FormFieldChoiceFactory(), FormFieldChoiceFactory()]

        for form_field_choice in form_field_choices:
            grant_role(self.viewer["role"], form_field_choice.get_privilege_ancestor(), self.viewer["user"])

        for form_field_choice in form_field_choices[1:]:
            grant_role(self.editor["role"], form_field_choice.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], form_field_choices[2].get_privilege_ancestor(), self.owner["user"])

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormFieldChoices"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormFieldChoices"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormFieldChoices"]["edges"]), 1)


class TestCreateFormFieldChoice(GQLTestCase):
    node_name = "FormFieldChoiceNode"
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        exclude_choices = [
            VariableDefinition.DATA_TYPE_CHOICES.stage,
            VariableDefinition.DATA_TYPE_CHOICES.dict,
            VariableDefinition.DATA_TYPE_CHOICES.list,
        ]
        self.variable_definition = VariableDefinitionFactory(
            data_type=random.choice(
                [choice for choice, _ in VariableDefinition.DATA_TYPE_CHOICES if choice not in exclude_choices]
            )
        )
        self.field = FormFieldFactory(variable_definition=self.variable_definition)
        self.td = {
            "field": self.field.gql_id,
            "value": random_dt_value(VariableDefinition.DATA_TYPE_CHOICES.str)
            if self.variable_definition.data_type != VariableDefinition.DATA_TYPE_CHOICES.choice
            else random.choice(list(self.variable_definition.variablechoiceitem_set.values_list('value', flat=True))),
            "order": random_dt_value(VariableDefinition.DATA_TYPE_CHOICES.int),
        }

        self.query = """
mutation CreateFormFieldChoice(
    $field: ID!,
    $value: String!,
    $order: Int!,
    ){
    createFormFieldChoice(input: {
        field: $field,
        value: $value,
        order: $order,
    }){
        formFieldChoiceEdge {
            node {
                id
                field {id}
                value
                order
            }
        }
    }
}
"""

    def test_create_requires_privileges(self):
        grant_role(self.viewer["role"], self.field.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_create_produces_formchoice(self):
        grant_role(self.owner["role"], self.field.get_privilege_ancestor(), self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.td.pop("field")
        self.assertEqual(
            self.field.gql_id, result["data"]["createFormFieldChoice"]["formFieldChoiceEdge"]["node"]["field"]["id"]
        )

        for field in self.td:
            result_value = result["data"]["createFormFieldChoice"]["formFieldChoiceEdge"]["node"][field]
            td_value = self.td[field]
            if isinstance(result_value, str):  # Due to returned values from enum fields
                result_value = result_value.lower()
                td_value = td_value.lower()
            self.assertEqual(result_value, td_value, msg=f"mismatch on {field}")

        lookup = FormFieldChoice.objects.get(
            id=from_global_id(result["data"]["createFormFieldChoice"]["formFieldChoiceEdge"]["node"]["id"])[1]
        )

        self.assertEqual(lookup.field, self.field)


class TestUpdateFormFieldChoice(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        exclude_choices = [
            VariableDefinition.DATA_TYPE_CHOICES.stage,
            VariableDefinition.DATA_TYPE_CHOICES.dict,
            VariableDefinition.DATA_TYPE_CHOICES.list,
        ]
        self.variable_definition = VariableDefinitionFactory(
            data_type=random.choice(
                [choice for choice, _ in VariableDefinition.DATA_TYPE_CHOICES if choice not in exclude_choices]
            )
        )
        self.field = FormFieldFactory(variable_definition=self.variable_definition)
        self.field_choice = FormFieldChoiceFactory(field=self.field)
        self.td = {
            "fieldChoiceId": self.field_choice.gql_id,
            "value": random_dt_value(VariableDefinition.DATA_TYPE_CHOICES.str)
            if self.variable_definition.data_type != VariableDefinition.DATA_TYPE_CHOICES.choice
            else random.choice(list(self.variable_definition.variablechoiceitem_set.values_list('value', flat=True))),
            "order": random_dt_value(VariableDefinition.DATA_TYPE_CHOICES.int),
        }

        self.query = """
mutation UpdateFormFieldChoice(
    $fieldChoiceId: ID!,
    $value: String!,
    $order: Int!,
    ){
    updateFormFieldChoice(input: {
        id: $fieldChoiceId,
        value: $value,
        order: $order,
    }){
        formFieldChoice {
            id
            field {id}
            value
            order
        }
    }
}
"""

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.field_choice.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.field_choice.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertEqual(result["data"]["updateFormFieldChoice"]["formFieldChoice"]["field"]["id"], self.field.gql_id)
        self.assertEqual(result["data"]["updateFormFieldChoice"]["formFieldChoice"]["order"], self.td['order'])
        self.assertEqual(result["data"]["updateFormFieldChoice"]["formFieldChoice"]["value"], self.td['value'])


class TestDeleteFormFieldChoice(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form_field_choice = FormFieldChoiceFactory()
        self.td = {"gqlId": self.form_field_choice.gql_id}
        self.query = """mutation DeleteFormFieldChoice($gqlId: ID!){ deleteFormFieldChoice(input: {id: $gqlId}){id}}"""

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.form_field_choice.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        FormFieldChoice.objects.get(pk=self.form_field_choice.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.form_field_choice.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteFormFieldChoice"]["id"])
        self.assertRaises(FormFieldChoice.DoesNotExist, FormFieldChoice.objects.get, **{"pk": self.form_field_choice.id})


class TestReadFormFieldChoiceTranslation(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        form_field_choice_translation = FormFieldChoiceTranslationFactory()
        self.td = {"gqlId": form_field_choice_translation.gql_id}
        self.form_field_choice_translation_query = """
query FormFieldChoiceTranslation($gqlId: ID!){
    formFieldChoiceTranslation(id: $gqlId){
        fieldChoice {id}
        caption
        language {id}
    }
}"""
        self.all_query = """
{
    allFormFieldChoiceTranslations{
        edges{
            node{
                fieldChoice {id}
                caption
                language {id}
            }
        }
    }
}"""

    def test_read_requires_login(self):
        result = self.gql_client.execute(self.form_field_choice_translation_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

        result = self.gql_client.execute(self.form_field_choice_translation_query, variable_values=self.td)
        self.assert_query_was_unauthorized(result)

    def test_read_filters_by_privilege(self):
        form_field_choice_translations = [
            FormFieldChoiceTranslationFactory(),
            FormFieldChoiceTranslationFactory(),
            FormFieldChoiceTranslationFactory(),
        ]

        for form_field_choice_translation in form_field_choice_translations:
            grant_role(self.viewer["role"], form_field_choice_translation.get_privilege_ancestor(), self.viewer["user"])

        for form_field_choice_translation in form_field_choice_translations[1:]:
            grant_role(self.editor["role"], form_field_choice_translation.get_privilege_ancestor(), self.editor["user"])

        grant_role(self.owner["role"], form_field_choice_translations[2].get_privilege_ancestor(), self.owner["user"])

        # Viewer
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.viewer["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormFieldChoiceTranslations"]["edges"]), 3)

        # Editor
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.editor["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormFieldChoiceTranslations"]["edges"]), 2)

        # Owner
        result = self.gql_client.execute(self.all_query, context_value=self.gql_client.get_context(user=self.owner["user"]))
        self.fail_on_errors(result)
        self.assertEqual(len(result["data"]["allFormFieldChoiceTranslations"]["edges"]), 1)


class TestCreateFormFieldChoiceTranslation(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.field_choice = FormFieldChoiceFactory()
        self.td = {
            "fieldChoice": self.field_choice.gql_id,
            "caption": "Read me read me wouldn't want to read me?",
            "language": get_gql_id('Language', Language.objects.order_by('?').values_list('iso_639_1', flat=True).first()),
        }

        self.query = """
mutation CreateFormFieldChoiceTranslation(
    $fieldChoice: ID!,
    $caption: String!,
    $language: ID!,
    ){
    createFormFieldChoiceTranslation(input: {
        fieldChoice: $fieldChoice,
        caption: $caption,
        language: $language,
    }){
        formFieldChoiceTranslationEdge {
            node {
                id
                fieldChoice {id}
                caption
                language {id}
            }
        }
    }
}
"""

    def test_create_requires_privileges(self):
        grant_role(self.viewer["role"], self.field_choice.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_create_produces_translation(self):
        grant_role(self.owner["role"], self.field_choice.get_privilege_ancestor(), self.owner["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.td.pop("fieldChoice")
        self.assertEqual(
            self.field_choice.gql_id,
            result["data"]["createFormFieldChoiceTranslation"]["formFieldChoiceTranslationEdge"]["node"]["fieldChoice"]["id"],
        )

        language_gql_id = self.td.pop("language")
        self.assertEqual(
            language_gql_id,
            result["data"]["createFormFieldChoiceTranslation"]["formFieldChoiceTranslationEdge"]["node"]["language"]["id"],
        )

        for field in self.td:
            result_value = result["data"]["createFormFieldChoiceTranslation"]["formFieldChoiceTranslationEdge"]["node"][field]
            td_value = self.td[field]
            if isinstance(result_value, str):  # Due to returned values from enum fields
                result_value = result_value.lower()
                td_value = td_value.lower()
            self.assertEqual(result_value, td_value, msg=f"mismatch on {field}")

        lookup = FormFieldChoiceTranslation.objects.get(
            id=from_global_id(
                result["data"]["createFormFieldChoiceTranslation"]["formFieldChoiceTranslationEdge"]["node"]["id"]
            )[1]
        )

        self.assertEqual(lookup.field_choice, self.field_choice)


class TestUpdateFormFieldChoiceTranslation(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.field_choice_translation = FormFieldChoiceTranslationFactory()
        self.td = {
            "formFieldChoiceTranslation": self.field_choice_translation.gql_id,
            "caption": "Read me read me wouldn't want to read me?",
            "language": get_gql_id('Language', Language.objects.order_by('?').values_list('iso_639_1', flat=True).first()),
        }

        self.query = """
mutation UpdateFormFieldChoiceTranslation(
    $formFieldChoiceTranslation: ID!,
    $caption: String!,
    $language: ID!,
    ){
    updateFormFieldChoiceTranslation(input: {
        id: $formFieldChoiceTranslation,
        caption: $caption,
        language: $language,
    }){
        formFieldChoiceTranslation {
            id
            fieldChoice {id}
            caption
            language {id}
        }
    }
}
"""

    def test_update_requires_privilege(self):
        grant_role(self.viewer["role"], self.field_choice_translation.get_privilege_ancestor(), self.viewer["user"])
        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

    def test_update_produces_result(self):
        grant_role(self.owner["role"], self.field_choice_translation.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertEqual(
            result["data"]["updateFormFieldChoiceTranslation"]["formFieldChoiceTranslation"]["fieldChoice"]["id"],
            self.field_choice_translation.field_choice.gql_id,
        )
        self.assertEqual(
            result["data"]["updateFormFieldChoiceTranslation"]["formFieldChoiceTranslation"]["caption"], self.td['caption']
        )
        self.assertEqual(
            result["data"]["updateFormFieldChoiceTranslation"]["formFieldChoiceTranslation"]["language"]["id"],
            self.td['language'],
        )


class TestDeleteFormFieldChoiceTranslation(GQLTestCase):
    gql_client = GQLTestCase.get_gql_client(graphene.Schema(query=TestQuery, mutation=TestMutation))

    def setUp(self):
        self.form_field_choice_translation = FormFieldChoiceTranslationFactory()
        self.td = {"gqlId": self.form_field_choice_translation.gql_id}
        self.query = """
mutation DeleteFormFieldChoiceTranslation($gqlId: ID!){
    deleteFormFieldChoiceTranslation(input: {id: $gqlId}){id}
}"""

    def test_delete_requires_privilege(self):
        grant_role(self.viewer["role"], self.form_field_choice_translation.get_privilege_ancestor(), self.viewer["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.viewer["user"])
        )
        self.assert_query_was_unauthorized(result)

        FormFieldChoiceTranslation.objects.get(pk=self.form_field_choice_translation.id)

    def test_delete_produces_result(self):
        grant_role(self.owner["role"], self.form_field_choice_translation.get_privilege_ancestor(), self.owner["user"])

        result = self.gql_client.execute(
            self.query, variable_values=self.td, context_value=self.gql_client.get_context(user=self.owner["user"])
        )
        self.fail_on_errors(result)

        self.assertTrue(result["data"]["deleteFormFieldChoiceTranslation"]["id"])
        self.assertRaises(
            FormFieldChoiceTranslation.DoesNotExist,
            FormFieldChoiceTranslation.objects.get,
            **{"pk": self.form_field_choice_translation.id},
        )
