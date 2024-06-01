from django.db.utils import IntegrityError


class EryTypeError(TypeError):
    pass


class EryValueError(ValueError):
    pass


class EryValidationError(Exception):
    pass


class EryDeserializationError(Exception):
    def __init__(self, **kwargs):
        self.message = self.generate_message(**kwargs)
        super().__init__()

    def __str__(self):
        return self.message

    @staticmethod
    def generate_message(**kwargs):
        """
        Returns a templated error message, with instance specific kwargs.

        Notes:
            - duplication: For reporting error in which unique instance already exists during nested_create.
                If the error occurs during a nested nested_create, (e.g., during creation of an ActionStep in
                order to create a ModuleDefinition), parent_cls (ModuleDefinition) is also reported.
            - child_dne: For reporting error in which attempt to retrieve related model using get (during nested create) fails
                due to a DoesNotExist error.
        """
        model_cls = kwargs['model_cls']
        ancestor = model_cls.get_privilege_ancestor_cls()
        if ancestor != model_cls:
            sub_message = " This error occured during the creation of {}".format(ancestor)
        else:
            sub_message = None

        details = kwargs['message']
        model_cls = kwargs['model_cls']
        data = kwargs['data']
        if 'duplicate' in details:
            message = f"Error creating model of class: {model_cls}, with data: {data}"
            message += ". An exact copy already exists in the database, and copies must be unique for this model class."
            if sub_message:
                message += sub_message
        elif 'null value' in details:
            words = details.split(' ')
            field = words[words.index('column') + 1]
            model_cls = kwargs['model_cls']
            message = f"Field: {field}, required for creation of model: {model_cls}"
            if sub_message:
                message += sub_message
        elif 'invalid keyword' in details:
            words = details.split(' ')
            field = words[0]
            message = f"Error: field: {field}, not present in model: {model_cls}."
            if sub_message:
                message += sub_message
        else:
            details = kwargs['message']
            message = f'Error occurred: {details}'
            if sub_message:
                message += sub_message
        return message


class EryIntegrityError(IntegrityError):
    def __init__(self, error_type, **kwargs):
        self.message = self.generate_message(error_type, **kwargs)
        super().__init__()

    def __str__(self):
        return self.message

    @staticmethod
    def generate_message(error_type, **kwargs):
        """
        Returns a templated error message, with instance specific kwargs.

        Notes:
            - child_dne: For reporting error in which attempt to retrieve related model (during nested create) fails
                due to equivalent of DoesNotExist.
            - multiple_child: For reporting error in which attempt to retrieve related model (during nested create) fails
                due to equivalent of MultipleObjectsReturned.
        """
        if error_type == 'child_dne':
            message = (
                f"Child of type, {kwargs['child_cls']}, with data, {kwargs['child_data']}, does not exist and"
                f" is required for creation of parent of type, {kwargs['parent_cls']},"
                f" with data: {kwargs['parent_data']}."
            )
        elif error_type == 'multiple_child':
            message = (
                f"Child of type, {kwargs['child_cls']}, with data, {kwargs['child_data']},"
                f" required for creation of parent of type, {kwargs['parent_cls']},"
                f" with data: {kwargs['parent_data']}, is not unique and cannot be retrieved."
            )
        return message
