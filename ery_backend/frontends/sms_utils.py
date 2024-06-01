from abc import ABC
import copy
from io import StringIO
import logging
import re

from lxml import etree

from django.db.models.functions import Lower

from ery_backend.hands.models import Hand
from ery_backend.modules.models import ModuleDefinitionWidget
from ery_backend.scripts.engine_client import evaluate_without_side_effects
from ery_backend.stint_specifications.models import StintSpecification
from ery_backend.stints.models import Stint
from ery_backend.users.models import User

logger = logging.getLogger(__name__)


def get_or_create_user(phone_number):
    try:
        user = User.objects.get(username='__phone_no__{}'.format(phone_number))
    except User.DoesNotExist:
        user = User.objects.create(username='__phone_no__{}'.format(phone_number), profile={'phone_no': phone_number})
        logger.info("Created User identified by phone_number '%s'.", phone_number)

    return user


def get_or_create_stint(opt_in_code, user, signal_pubsub=True):
    """
        Use opt-in to find and initialize correct :class:`~ery_backend.stint_specifications.models.StintSpecification`.

        Args:
            - signal_pubsub (bool): Whether to send a signal to the Robot Runner using Google Pubsub during stint.start.
        Returns:
            :class:`~ery_backend.stints.models.Stint`
    """
    from ery_backend.frontends.models import Frontend

    try:
        stint_specification = StintSpecification.objects.get(opt_in_code=opt_in_code)
    except StintSpecification.DoesNotExist:
        logger.warning("The User '%s' is trying to use unused opt-in code '%s'.", user, opt_in_code)
        return None

    hand = Hand.objects.filter(
        stint__status=Stint.STATUS_CHOICES.running, stint__stint_specification=stint_specification, user=user
    )
    if hand:
        return hand.first().stint

    sms = Frontend.objects.get(name='SMS')
    if stint_specification.late_arrival:
        stint = stint_specification.stints.filter(status=Stint.STATUS_CHOICES.running).first()
        if stint:
            stint.join_user(user, sms)
            return stint
    stint = stint_specification.realize(user)
    Hand.objects.create(
        user=user,
        stint=stint,
        frontend=sms,
        language=stint.stint_specification.allowed_language_frontend_combinations.first().language,
    )
    stint.start(user, signal_pubsub)

    return stint


def is_opt_in(message):
    """
    Confirm whether message is an opt in code for a :class:`~ery_backend.stint_specifications.models.StintSpecification`.

    Args:
        message (str): Text message sent by sms :class:`~ery_backend.users.models.User`

    Returns:
        bool
    """
    return (
        StintSpecification.objects.annotate(opt_in_code_lower=Lower('opt_in_code'))
        .filter(opt_in_code_lower=message.lower().replace(' ', ''))
        .exists()
    )


def opt_in(opt_in_code, phone_number, signal_pubsub=True):
    """
    Log SMS :class:`~ery_backend.users.models.User` into :class:`~ery_backend.stints.models.Stint`.

    Args:
        - opt_in_code (str): Used to locate correct :class:`~ery_backend.stints.models.Stint' via
          :class:`~ery_backend.stint_specifications.models.StintSpecification`.
        - phone_number (str): Used to locate :class:`~ery_backend.users.models.User` being connected to
          :class:`~ery_backend.stints.models.Stint`.
        -signal_pubsub (bool): Whether to send a signal to the Robot Runner using Google Pubsub during stint.start.
    Returns:
        hand (:class:`~ery_backend.hands.models.Hand`): Object connecting :class:`~ery_backend.users.models.User`
          to :class:`~ery_backend.stints.models.Stint`.
    """
    user = get_or_create_user(phone_number)
    correct_code = (
        StintSpecification.objects.annotate(opt_in_code_lower=Lower('opt_in_code'))
        .get(opt_in_code_lower=opt_in_code.lower().replace(' ', ''))
        .opt_in_code
    )
    stint = get_or_create_stint(correct_code, user, signal_pubsub)
    hand = stint.hands.get(user=user)
    return hand


def get_sms_hand(message, phone_number):
    user = get_or_create_user(phone_number)
    # an sms user can be associated with one active stint at a time
    hands = user.hands.filter(stint__status=Stint.STATUS_CHOICES.running, status=Hand.STATUS_CHOICES.active)

    if hands:
        return hands.first()

    return None


def set_widget_variable(hand, sms_input, message):
    hand.stint.set_variable(sms_input.variable_definition, message, hand)


def get_or_create_sms_stage(hand):
    """
    Get or create :class:`~ery_backend.frontends.models.SMSStage` :class:`~ery_backend.hands.models.Hand`
      instance's :class:`~ery_backend.stages.models.Stage` if exists.

    Args:
        hand (:class:`~ery_backend.hands.models.Hand`): Provides :class:`~ery_backend.stages.models.Stage`
          for verification.

    Returns:
        Union[bool, None]
    """
    from .models import SMSStage

    return SMSStage.objects.get_or_create(stage=hand.stage)[0]


def _get_elements(tree):
    """
    Get lxml elements, which wrap each node of tree.
    """
    return list(tree.getroot())


def _get_element_tags(tree):
    return [element.tag for element in _get_elements(tree)]


# XXX: Not sure if we need this
# def _get_block_tags(tag_name, blocks, parser):
#     """
#     Recursively parse blocks into set of lxml elements.
#     """
#     jsx_set = set()
#     tree = get_xml_tree(blocks[tag_name], parser)
#     tags = _get_element_tags(tree)
#     if tags:
#         for tag in tags:
#             jsx_set.update([tag])
#             # get sub_tags
#             sub_tags = _get_block_tags(tag, blocks, parser)
#             if sub_tags:
#                 jsx_set.update(sub_tags)

#     return jsx_set


# def get_block_tags(tag_name, blocks):
#     """
#     Get set of unique jsx tags from content of block matching tag_name.

#     Args:
#         tag_name (str): Used to obtain block from blocks.
#         blocks (Dict['str': 'str']): block name, content pairs.

#     Returns:
#         Set[str]: All unique tags recursively obtained from original content body and its sub-tags.

#     Notes:
#         - Uses etree XMLParser for tag parsing. See http://lxml.de/3.1/parsing.html
#     """
#     parser = etree.XMLParser()
#     tags = _get_block_tags(tag_name, blocks, parser)
#     return tags


class SMSRenderer(ABC):
    """
    Contains methods necessary for rendering content for SMS
    :class:`~ery_backend.frontends.models.Frontend` instances.
    """

    parser = etree.XMLParser()

    def __init__(self, hand):
        from ery_backend.frontends.models import Frontend

        self.frontend = Frontend.objects.get(name='SMS')
        self.hand = hand

    def _fill_in_element(self, element, blocks, widgets, current_block_info=None):
        """
        Find and replace tag declarations with their content.

        Args:
            - element (:class:`lxml.etree.Element`)
            - blocks (Dict[str: str]): Collection of elements belonging to
              :class:`~ery_backend.base.models.EryModel` used to create tree.
            - widgets List[Union[:class:`ery_backend.templates.models.TemplateWidget`,
                :class:`ery_backend.modules.models.ModuleDefinitionWidget`]]: Related widgets.
            - current_block_info (Dict[str, str]): Holds current block's type and ancestral_id (if found).
              Used for recursion.
        """
        if not current_block_info:
            current_block_info = {'block_type': blocks['Root']['block_type'], 'ancestor_id': blocks['Root']['ancestor_id']}
        block_type = current_block_info['block_type']
        ancestor_id = current_block_info['ancestor_id']  # pre-allocated for non-block tags.
        if element.tag in blocks:
            block_type = blocks[element.tag]['block_type']
            ancestor_id = blocks[element.tag]['ancestor_id']
            current_block_info['block_type'] = block_type
            current_block_info['ancestor_id'] = ancestor_id
            subcontent = blocks[element.tag]['content']
            subtree = self.get_xml_tree(subcontent, self.parser)
            subelements = subtree.getroot().getchildren()
            if not subelements:
                element.text = subcontent
        else:
            subelements = element.getchildren()
        if subelements:
            first_element = subelements[0]  # first element is next to preceding text, if any
            for subelement in subelements:
                if subelement == first_element:
                    preceding_text = ''.join(subelement.xpath("preceding-sibling::*/text()|preceding-sibling::text()"))
                    element.text = preceding_text
                self._fill_in_element(subelement, blocks, widgets, copy.deepcopy(current_block_info))
                current_block_info['block_type'] = current_block_info['block_type']
                current_block_info['ancestor_id'] = ancestor_id
                element.append(subelement)

        if widgets:
            if self._is_widget(element):
                widget_name = element.tag.replace('Widget.', '')
                widget_key = f"{widget_name}-{current_block_info['block_type']}-{current_block_info['ancestor_id']}"
                element.text = widgets[widget_key]

    def create_tree(self, root_name, root_content, blocks, widgets=None):
        """
        Builds a hierarchical tree by parsing related block content.

        Args:
            - root_name (str): Name of topmost element.
            - root_content (str): Content belonging to topmost element.
            - blocks (Dict[str: str]): Referring to
              :class:`~ery_backend.stages.models.StageTemplateBlock`,
              :class:`~ery_backend.templates.models.TemplateBlock`,
              :class:`~ery_backend.commands.models.CommandTemplateBlock`
              instances.
            - widgets (Optional[List[Union[:class:`ery_backend.templates.models.TemplateWidget`, \
:class:`ery_backend.modules.models.ModuleDefinitionWidget`]]]): Related widgets.

        Returns:
            :class:`lxml.etree.Element`: Root element of tree.
        """
        tree = self.get_xml_tree(blocks[root_name]['content'], parser=self.parser, wrapper=root_name)
        root = tree.getroot()
        for element in root:
            self._fill_in_element(element, blocks, widgets)
        return root

    @classmethod
    def compile_sms_content(cls, element):
        """
        Convert :class:`lxml.etree.Element` instance (and its children) into a single
        string for presentation over SMS.

        Args:
            - element (:class:`lxml.etree.Element`)

        Returns:
            str
        """
        output = element.text if element.text else ''
        for subelement in element:
            output += cls.get_element_content(subelement)
        return output

    @classmethod
    def get_xml_tree(cls, content, parser, wrapper='wrapper'):
        """
        Create an etree object, with in-content tags as nodes.
        """
        return etree.parse(StringIO(f'<{wrapper}>{content}</{wrapper}>'), cls.parser)  # Convert str to tree

    def render_widget(self, widget_wrapper, **kwargs):
        # pylint:disable=anomalous-backslash-in-string
        """
        Render code for use on the SMS :class:`~ery_backend.frontend.models.Frontend`.

        Args:
            - widget_wrapper (Union[:class:`~ery_backend.templates.models.TemplateWidget`,
                                    :class:`~ery_backend.modules.models.ModuleDefinitionWidget`).
            - \*\*kwargs (Dict): Contains extra protobuff Variable messages to be included in the context for server side \
              evaluation calls.

        Returns:
            str
        """
        extra_variables = {}

        if isinstance(widget_wrapper, ModuleDefinitionWidget):
            if widget_wrapper.is_multiple_choice:
                extra_variables.update(
                    widget_wrapper.get_choices_as_extra_variable(self.hand.current_module_definition.primary_language)
                )  # XXX: Should be using the hand's language?
        if 'extra_variables' in kwargs:
            extra_variables.update(kwargs['extra_variables'].items())

        widget = widget_wrapper.widget
        return evaluate_without_side_effects(f'render_{widget}', widget.code, self.hand, extra_variables=extra_variables)

    @staticmethod
    def _is_widget(element):
        regex_pattern = r'(Widget\.){1}(.)*'
        return re.match(regex_pattern, element.tag) is not None

    def get_widgets_from_element(self, element, blocks, widget_info=None, output=None):
        """
        Recursively search element and its children for :class:`~ery_backend.modules.models.ModuleDefinitionWidget`
        and :class:`~ery_backend.templates.models.TemplateWidget` instances.

        Args:
            - element (:class:`lxml.etree.Element`): Holds tag name.
            - blocks (Dict[str, str]): Name, class name, and ancestor_id of related
              :class:`ery_backend.stages.models.StageTemplateBlock`, :class:`~ery_backend.templates.models.TemplateBlock`]
              instances.
            - widget_info (Dict[str, str]): Holds widget name, wrapping block's type and ancestral_id (if found).
              Used for recursion.
            - output (List[str]): Holds composite keys generated using widget_info used to obtain corresponding instances
              via :py:meth:`SMSRenderer.get_sms_widgets`.

        Returns:
            List[str]: Returns composite keys made from element names, block_types, and ancestor ids (if any).
        """
        is_widget = self._is_widget(element)
        if not output:
            output = []
        if not widget_info:
            widget_info = {
                'widget': None,
                'block_type': blocks['Root']['block_type'],
                'ancestor_id': blocks['Root']['ancestor_id'],
            }
        block_type = widget_info['block_type']
        ancestor_id = widget_info['ancestor_id']  # pre-allocated for non-block tags.
        if not is_widget:
            if element.tag in blocks:
                content = blocks[element.tag]['content']
                block_type = blocks[element.tag]['block_type']
                ancestor_id = blocks[element.tag]['ancestor_id']
                widget_info["block_type"] = block_type
                widget_info["ancestor_id"] = ancestor_id
                subtree = self.get_xml_tree(content, self.parser)
                subelements = subtree.getroot().getchildren()
            else:
                subelements = element.getchildren()

            for subelement in subelements:
                output = self.get_widgets_from_element(subelement, blocks, copy.deepcopy(widget_info), output)
                widget_info["block_type"] = block_type
                widget_info["ancestor_id"] = ancestor_id
        else:
            widget_info['widget'] = element.tag.split('.')[-1]
            output_key = f"{widget_info['widget']}-{widget_info['block_type']}-{widget_info['ancestor_id']}"
            if output_key not in output:
                output.append(output_key)
        return output

    def get_sms_widgets(self):
        """
        Search related content for :class:`~ery_backend.modules.models.ModuleDefinitionWidget` and/or
        :class:`~ery_backend.templates.models.TemplateWidget` instances.

        Returns:
            Dict[str, Union[:class:`~ery_backend.modules.models.ModuleDefinitionWidget`,
                :class:`~ery_backend.templates.models.TemplateWidget`]]: Key is widget composite key
                (see :py:meth:`get_widgets_from_element`) and value is corresponding widget.
        """
        from ery_backend.frontends.models import Frontend
        from ery_backend.stages.models import StageTemplateBlock
        from ery_backend.templates.models import TemplateWidget

        widgets = {}
        sms = Frontend.objects.get(name='SMS')
        blocks = self.stage_template.get_blocks(self.hand.frontend, self.hand.language)
        root_block = self.stage_template.get_root_block()
        tree = self.get_xml_tree(blocks[root_block.name]['content'], parser=self.parser, wrapper=root_block.name)
        root = tree.getroot()
        widget_keys = self.get_widgets_from_element(root, blocks)
        if widget_keys:
            for widget_key in widget_keys:
                name, block_type, ancestor_id = widget_key.split('-')
                if block_type == StageTemplateBlock.__name__:
                    widgets[widget_key] = ModuleDefinitionWidget.objects.get(
                        module_definition__id=ancestor_id, name=name, widget__frontend=sms
                    )
                else:
                    widgets[widget_key] = TemplateWidget.objects.get(template__id=ancestor_id, name=name, widget__frontend=sms)
        return widgets

    @classmethod
    def get_element_content(cls, element):
        """
        Convert element into a str.

        Args:
            element (:class:`lxml.etree.Element`)

        Returns:
            str
        """
        output = ''
        if element.text:
            output += element.text
        for subelement in element:  # element may have text and subelements if it starts with text before a tag is declared
            output += cls.get_element_content(subelement)
        if element.tail:
            output += element.tail
        return output


class SMSCommandTemplateRenderer(SMSRenderer):
    """
    Used to render instances of :class:`~ery_backend.commands.models.CommandTemplate` for SMS
    :class:`~ery_backend.frontends.models.Frontend` instances.
    """

    def __init__(self, command_template, hand):
        super().__init__(hand)
        self.command_template = command_template

    def render(self):
        """
        Compile string from all blocks relevant to :class:`~ery_backend.commands.models.CommandTemplate`.

        Notes:
            - The :class:`~ery_backend.hands.models.Hand` :class:`SMSRenderer` provides the required
              :class:`~languages_plus.models.Language` of the returned content.

        Returns:
            str
        """
        blocks = self.command_template.get_blocks(self.hand.frontend, self.hand.language)
        root_block = self.command_template.get_root_block()
        root = self.create_tree(root_block.name, blocks[root_block.name]['content'], blocks)
        output = self.compile_sms_content(root)
        return output


class SMSStageTemplateRenderer(SMSRenderer):
    """
    Used to render instances of :class:`~ery_backend.stages.models.StageTemplate` for SMS
    :class:`~ery_backend.frontends.models.Frontend` instances.
    """

    def __init__(self, stage_template, hand):
        super().__init__(hand)
        self.stage_template = stage_template

    def render(self):
        """
        Compile string from all blocks relevant to :class:`~ery_backend.stages.models.StageTemplate`.

        Notes:
            - The :class:`~ery_backend.hands.models.Hand` :class:`SMSRenderer` provides the required
              :class:`~languages_plus.models.Language` of the returned content.

        Returns:
            str
        """
        blocks = self.stage_template.get_blocks(self.hand.frontend, self.hand.language)
        widgets = {key: self.render_widget(widget_wrapper) for (key, widget_wrapper) in self.get_sms_widgets().items()}
        root_block = self.stage_template.get_root_block()
        root = self.create_tree(root_block.name, blocks[root_block.name]['content'], blocks, widgets)
        output = self.compile_sms_content(root)
        return output
