import graphene

from .models import FormItem
from .schema import FormFieldNode, FormButtonListNode


BaseFormFieldInput = FormFieldNode.get_mutation_input()
BaseCreateFormField = FormFieldNode.get_create_mutation_class(BaseFormFieldInput)


class CreateFormField(BaseCreateFormField):
    class Input(BaseFormFieldInput):
        form_item = graphene.ID(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        form_item_pk = cls.gql_id_to_pk(inputs.get('form_item'))
        form_item = FormItem.objects.get(pk=form_item_pk)
        output = super().mutate_and_get_payload(root, info, **inputs)
        form_field = output.form_field_edge.node
        form_item.field = form_field
        form_item.save()
        return output


BaseFormButtonListInput = FormButtonListNode.get_mutation_input()
BaseCreateFormButtonList = FormButtonListNode.get_create_mutation_class(BaseFormButtonListInput)


class CreateFormButtonList(BaseCreateFormButtonList):
    class Input(BaseFormButtonListInput):
        form_item = graphene.ID(required=True)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **inputs):
        form_item_pk = cls.gql_id_to_pk(inputs.get('form_item'))
        form_item = FormItem.objects.get(pk=form_item_pk)
        output = super().mutate_and_get_payload(root, info, **inputs)
        button_list = output.form_button_list_edge.node
        form_item.button_list = button_list
        form_item.save()
        return output
