from time import sleep

from graphql_relay import to_global_id
from google.cloud import datastore

from ery_backend.actions.factories import ActionStepFactory
from ery_backend.actions.models import ActionStep
from ery_backend.base.testcases import EryTestCase, EryLiveServerTestCase, create_test_hands
from ery_backend.datastore.factories import testable_entity_set
from ery_backend.users.factories import UserFactory
from ery_backend.stints.factories import StintFactory
from ery_backend.variables.factories import HandVariableFactory
from ery_backend.roles.models import Role
from ery_backend.roles.utils import grant_role

# XXX : While disabling
# pylint: disable-all
class TestDatastoreRunSaverIntegration(EryTestCase):
    """
    The DatastoreRunSaver saves the specified heirarchy
    """

    def setUp(self):
        raise NotImplementedError("The RunSaver Integration tests need a rewrite for the new DatastoreRunsaver")

        self.hand = create_test_hands(n=1).first()
        self.hand_variable = HandVariableFactory(hand=self.hand)
        vd = self.hand_variable.variable_definition
        vd.module_definition = self.hand.current_module.stint_definition_module_definition.module_definition
        self.hand_variable.variable_definition.save()
        self.action_step = ActionStepFactory(for_each=ActionStep.FOR_EACH_CHOICES.current_hand_only)
        self.action_step.action.module_definition = self.hand_variable.variable_definition.module_definition
        self.action_step.save()

    def test_status(self):
        raise AssertionError("The RunSaver Integration tests need a rewrite for the new DatastoreRunsaver")

    def test_integrated_save(self):
        """
        ActionStep.run saves a google datastore entity
        """
        self.action_step.run(self.hand)

        client = datastore.Client()
        query = client.query(kind="Hand")
        query.add_filter("pk", "=", self.hand.pk)
        result = list(query.fetch())
        self.assertFalse(len(result) == 0)

    def test_save_works(self):
        """
        DatastoreRunSaver.save_vars the correct datastore tree
        """
        drs = DatastoreRunSaver(self.action_step, self.hand.stint)
        run = drs.save_vars(self.action_step, self.hand)

        client = datastore.Client()
        self.assertIsNot(client.get(run.key), None)

        sleep(0.25)
        r = list(client.query(kind="Hand", ancestor=run.key).fetch())
        self.assertEqual(len(r), 1, msg="wrong number of hands for this run")


class TestDatastoreCSV(EryLiveServerTestCase):
    """Datastore CSV data should be accessible via view"""

    def test_full_set(self):
        """The response CSV correctly includes complete a complete dataset"""

        user = UserFactory()
        stint1 = StintFactory()
        stint1_id = to_global_id("StintNode", stint1.pk)
        stint2 = StintFactory()

        grant_role(Role.objects.get(name="owner"), stint1.get_privilege_ancestor(), user)

        ds = datastore.Client()
        visible_entities = testable_entity_set(stint_pk=stint1.pk)
        hidden_entities = testable_entity_set(stint_pk=stint2.pk)

        with ds.transaction():
            ds.put_multi(visible_entities)
            ds.put_multi(hidden_entities)

        client = self.get_loggedin_client(user)
        response = client.get(f"/stint/{stint1_id}/data/")
        text = response.content.decode("utf-8")

        for entity in visible_entities[2:]:
            saved = ds.get(entity.key)

            if saved is None:
                raise AssertionError("Google datastore failed to save test data.")

            msg = (
                f'Saved  - Name: {saved["name"]}  - Key: {saved.key}\n'
                + f'Entity - Name: {entity["name"]} - Key: {entity.key}'
            )

            self.assertIn(entity["name"], text, msg=msg)

            for key in entity["variables"].keys():
                self.assertIn(
                    key, text, msg=f'Kind: {entity.kind}  Name: {entity["name"]} is missing variable in response csv'
                )

        for entity in hidden_entities[2:]:
            saved = ds.get(entity.key)

            if saved is None:
                raise AssertionError("Google datastore failed to save test data.")

            self.assertNotIn(entity["name"], text, msg=f'Kind: {entity.kind}  Name: {entity["name"]} included in response csv')

            for key in entity["variables"].keys():
                self.assertNotIn(
                    key, text, msg=f'Kind: {entity.kind}  Name: {entity["name"]} variable included in response csv'
                )
