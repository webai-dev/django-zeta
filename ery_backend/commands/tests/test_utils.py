from ery_backend.base.testcases import EryTestCase
from ery_backend.modules.factories import ModuleDefinitionFactory

from ..factories import CommandFactory
from ..utils import get_command


class TestPatternLookup(EryTestCase):
    def setUp(self):
        self.module_definition = ModuleDefinitionFactory()
        self.trigger_pattern = r'HLP[\w\W]*'
        self.command = CommandFactory(module_definition=self.module_definition, trigger_pattern=self.trigger_pattern)

    def test_trigger_pattern(self):
        """
        Confirm regex based filtering of commands.
        """
        # match present
        trigger_word = 'HLPMePleaz'
        self.assertEqual(get_command(trigger_word, self.module_definition), self.command)

        # match not present
        trigger_word = 'PleazHelpMeh'
        self.assertIsNone(get_command(trigger_word, self.module_definition))
