from ery_backend.base.testcases import EryTestCase, create_test_hands
from ery_backend.syncs.factories import EraFactory
from ..models import Log
from ..factories import LogFactory


class TestLog(EryTestCase):
    def setUp(self):
        self.hand = create_test_hands(n=1, signal_pubsub=False).first()
        self.team = self.hand.current_team
        self.era = EraFactory(module_definition=self.hand.current_module_definition)
        self.module = self.hand.current_module
        self.stint = self.hand.stint
        self.message = 'This log was made by a log factory, which was made by a man wearing' ' flannel!'
        self.era_log = LogFactory(message=self.message, era=self.era, team=self.team)
        self.log = LogFactory(message=self.message, stint=self.stint, log_type=Log.LOG_TYPE_CHOICES.info)
        self.module_log = LogFactory(
            message=self.message, stint=self.stint, log_type=Log.LOG_TYPE_CHOICES.info, module=self.module, hand=self.hand
        )

    def test_exists(self):
        self.assertIsNotNone(self.log)

    def test_expected_attributes(self):
        self.log.refresh_from_db()
        self.module_log.refresh_from_db()
        self.assertEqual(self.log.stint, self.stint)
        self.assertEqual(self.log.message, self.message)
        self.assertEqual(self.log.log_type, Log.LOG_TYPE_CHOICES.info)
        self.assertEqual(self.module_log.module, self.module)
        self.assertEqual(self.module_log.hand, self.hand)
        self.assertEqual(self.era_log.era, self.era)
        self.assertEqual(self.era_log.team, self.team)
