class FileNodeMixin:
    @classmethod
    def get_node(cls, info, node_id):
        return super().get_node(info, node_id, exclude_kwargs={'state': cls._meta.model.STATE_CHOICES.deleted})
