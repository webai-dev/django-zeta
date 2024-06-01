from unittest import mock
import unittest

from ery_backend.users.factories import UserFactory
from ery_backend.base.testcases import EryLiveServerTestCase
from ery_backend.hands.models import Hand

from ..factories import StintFactory


@unittest.skip("Address in issue #826")
class TestRenderWeb(EryLiveServerTestCase):
    """Test the renderweb function"""

    @classmethod
    def setUp(cls, *args, **kwargs):
        super().setUpClass(*args, **kwargs)

        cls.user = UserFactory()
        cls.stint = StintFactory()
        hand = Hand(user=cls.user, stint=cls.stint)
        hand.save()

    @mock.patch('ery_backend.stints.models.StintDefinition.render_web')
    def test_graphql_id(self, mock_render):
        """Stint view should retrieve a stint from the graphql global id"""
        mock_render.return_value = '<html>Example</html>'
        stint_id = self.stint.gql_id
        client = self.get_loggedin_client(self.user)

        response = client.get(f"/stints/{stint_id}/")
        self.assertEqual(response.status_code, 200)

    def test_reject_django_id(self):
        """Stint view should refuse raw django ids"""
        client = self.get_loggedin_client(self.user)
        response = client.get(f"/stints/{self.stint.pk}/")
        self.assertEqual(response.status_code, 400)
