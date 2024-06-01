import re

# from ery_backend.templates.models import Template

# from .models import Command, CommandTemplate, CommandTemplateBlock, \
#    CommandTemplateBlockTranslation


def get_command(trigger_word, module_definition):
    """
    Obtain :class:`~ery_backend.commands.models.Command` with pattern matching trigger_word.

    Args:
        - trigger_word (str): Matched against :class:`~ery_backend.commands.models.Command` trigger_pattern.
        - module_definition (:class:`~ery_backend.modules.models.ModuleDefinition`): Parental to all \
          :class:`~ery_backend.commands.models.Command` instances.

    Returns:
        :class:`~ery_backend.commands.models.Command`
    """
    patterns = module_definition.command_set.values_list('trigger_pattern', flat=True)
    for pattern in patterns:
        match = re.match(pattern, trigger_word)
        if match:
            return module_definition.command_set.get(trigger_pattern=pattern)
    return None


def assign_default_commands(sender, instance, **kwargs):
    """
    Signal reciever function for assigning default :class:`~ery_backend.commands.models.Command` instances on
    creation of new :class:`~ery_backend.module.models.ModuleDefinition`.

    Args:
        - sender (:class:`django.db.models.Signal`)
        - instance (:class:`~ery_backend.modules.models.ModuleDefintiion`): Parental instance to which \
          :class:`~ery_backend.commands.models.Command` instances are assigned.
    """


#    if kwargs['created']:
#        default_sms_template = Template.objects.get(name='default-sms-command-template')
#        sms_frontend = default_sms_template.frontend
#
#        help_command = Command.objects.create(
#            module_definition=instance, action=None,
#            trigger_pattern=r'([Hh]+[Ee]+[Ll]+[Pp]+)|([?]+)',
#            name='help')
#        help_content = """
# Quit: Opts-out user from Stint,
# """
#        # Will be used in issue #276
#        help_co = CommandTemplate.objects.create(template=default_sms_template, command=help_command)
#        help_ctb = CommandTemplateBlock.objects.create(command_template=help_co, name='Content')
#        CommandTemplateBlockTranslation.objects.create(
#            command_template_block=help_ctb, language=instance.primary_language, content=help_content, frontend=sms_frontend)

# XXX: Address in issue #538
# Command.objects.create(
#     module_definition=instance, action=back_action,
#     trigger_pattern=r'[Bb]+[Aa]+[Cc]+[Kk]+',
#     name='back')

# Command.objects.create(
#     module_definition=instance, action=next_action,
#     trigger_pattern=r'[Nn]+[Ee]+[Xx]+[Tt]+',
#     name='next'
# )

# quit_command = Command.objects.create(
#     module_definition=instance, action=quit_action,
#     trigger_pattern=r'[Qq]+[Uu]+[Ii]+[Tt]+',
#     name='quit'
# )

# Will be used in issue #276
# quit_co = CommandTemplate.objects.create(template=default_sms_template, command=quit_command)
# ctb = CommandTemplateBlock.objects.create(command_template=quit_co, name='Content')
# CommandTemplateBlockTranslation.objects.create(
#     command_template_block=ctb, language=instance.primary_language,
#     content="Task stopped. Thank you for participating!", frontend=sms_frontend)
