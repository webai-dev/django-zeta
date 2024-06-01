from unittest import mock
from ery_backend.base.testcases import EryTestCase, create_test_hands


class TestViews(EryTestCase):
    @mock.patch('ery_backend.stages.models.StageDefinition.render')
    def test_render_sms(self, mock_render):
        """
        Confirm correct hand located through render_sms, with expected response.
        """
        from ..sms_views import render_sms

        mock_render.return_value = 'whatitshouldbe'
        hand = create_test_hands(n=1, frontend_type='SMS', signal_pubsub=False).first()
        hand.stint.stint_specification.opt_in_code = 'getyouone'
        hand.stint.stint_specification.save()
        phone_number = '1-800-588-2300'  # Empiiiirreee, today
        hand.user.username = f'__phone_no__{phone_number}'
        hand.user.save()
        text = render_sms(hand)
        self.assertEqual(text, "whatitshouldbe")
