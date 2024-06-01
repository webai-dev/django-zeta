class EryActionError(Exception):
    def __init__(self, action_step, original_error, hand, **kwargs):
        self.message = self.generate_message(action_step=action_step, original_error=original_error, hand=hand)
        super().__init__()

    def __str__(self):
        return self.message

    @staticmethod
    def generate_message(**kwargs):
        """
        Returns a templated error message, with instance specific kwargs.
        """
        message = (
            f"Error running {kwargs['action_step']} of type: {kwargs['action_step'].action_type}."
            f" with hand: {kwargs['hand']}. Specifically: {kwargs['original_error']}"
        )
        return message
