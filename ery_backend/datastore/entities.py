from datetime import datetime
from google.cloud import datastore
from pytz import timezone

from django.conf import settings


from .ery_client import get_datastore_client


csv_fields = [
    "run_started",
    "stint_specification",
    "started_by",
    "lab",
    "action_step_id",
    "stint_id",
    "team_id",
    "team_name",
    "team_era",
    "hand_id",
    "hand_name",
    "hand_era",
    "hand_current_team",
    "hand_stage",
]


class FromEntityMixin:
    @classmethod
    def from_entity(cls, entity):
        """Wrap the generic :class:`google.cloud.datastore.Entity` with the ery Entity"""
        return cls(parent=entity.key.parent, key=entity.key, **entity)


class RunEntity(FromEntityMixin, datastore.Entity):
    """Ery Datstore Run Entity"""

    def __init__(
        self,
        pk,
        *args,
        stint_definition_name=None,
        stint_definition_id=None,
        stint_specification_name=None,
        stint_specification_id=None,
        started_by=None,
        lab=None,
        started=None,
        ended=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self["pk"] = pk
        if self.key is None:
            self.key = self._make_key()

        if stint_definition_name is not None:
            self["stint_definition_name"] = stint_definition_name

        if stint_definition_id is not None:
            self["stint_definition_id"] = stint_definition_id

        if stint_specification_name is not None:
            self["stint_specification_name"] = stint_specification_name

        if stint_specification_id is not None:
            self["stint_specification_id"] = stint_specification_id

        if started_by is not None:
            self["started_by"] = started_by

        if lab is not None:
            self["lab"] = lab

        if started is not None:
            self["started"] = started

        if ended is not None:
            self["ended"] = ended

    def _make_key(self):
        """
        Create a new key for initialization.
        """
        client = get_datastore_client()
        return client.key("Run", self["pk"])

    @classmethod
    def from_entity(cls, entity):
        """Wrap the generic :class:`google.cloud.datastore.Entity` with the ery Entity"""
        return cls(key=entity.key, **entity)

    @staticmethod
    def from_django(stint):
        """
        Create a :class:`RunEntity`

        Args:
            - stint (:class:`~ery_backend.stints.models.Stint`)

        Returns:
            :class:`RunEntity`
        """
        entity = RunEntity(
            pk=stint.pk,
            stint_definition_name=stint.stint_specification.stint_definition.name,
            stint_definition_id=stint.stint_specification.stint_definition.pk,
            stint_specification_name=stint.stint_specification.name,
            stint_specification_id=stint.stint_specification.pk,
            started_by=stint.started_by.username,
            lab=stint.lab.name if stint.lab else None,
            started=stint.started,
            ended=stint.ended,
        )
        return entity

    @property
    def csv_data(self):
        """Return a dict describing the csv fields that can be deduced from this entity"""
        output = {
            "stint_id": self["pk"],
            "stint_specification": self["stint_specification_name"],
            "started_by": self["started_by"],
        }
        if "lab" in self:
            output["lab"] = self["lab"]
        return output


class WriteEntity(FromEntityMixin, datastore.Entity):
    """Ery Datastore Write Entity"""

    def __init__(
        self,
        parent,
        *args,
        pk=None,
        action_name=None,
        action_step_id=None,
        module_name=None,
        module_id=None,
        current_module_index=None,
        era_name=None,
        era_id=None,
        variables=None,
        **kwargs,
    ):
        """
        Args:
            pk: :class:`~ery_backend.actions.models.ActionStep.pk`
            parent:  :class:`google.cloud.datastore.Client.key`
        """
        super().__init__(*args, **kwargs)

        if pk is None:
            tz = timezone(settings.TIME_ZONE)
            self["pk"] = datetime.now(tz)
        else:
            self["pk"] = pk

        if self.key is None:
            self.key = self._make_key(self["pk"].isoformat(), parent)

        if action_name is not None:
            self["action_name"] = action_name

        if action_step_id is not None:
            self["action_step_id"] = action_step_id

        if module_name is not None:
            self["module_name"] = module_name

        if module_id is not None:
            self["module_id"] = module_id

        if current_module_index is not None:
            self["current_module_index"] = current_module_index

        if era_name is not None:
            self["era_name"] = era_name

        if era_id is not None:
            self["era_id"] = era_id

        if variables is not None:
            self["variables"] = variables

    @staticmethod
    def _make_key(pk, parent):
        """
        Create a new key for initialization.
        """
        client = get_datastore_client()
        return client.key("Write", pk, parent=parent)

    @staticmethod
    def from_django(action_step, variables, hand, parent=None):
        """
        Create a :class:`WriteEntity`

        Args:
            - action_step (:class:`~ery_backend.actions.models.ActionStep`)
            - hand (:class:`~ery_backend.hands.models.Hand`)
            - parent (Optional[:class:`google.cloud.datastore.Client.key`]): set the entity's datastore ancestor

        Returns:
            :class:`WriteEntity`
        """
        return WriteEntity(
            parent=parent,
            action_name=action_step.action.name,
            action_step_id=action_step.pk,
            module_name=action_step.action.module_definition.name,
            module_id=action_step.action.module_definition.pk,
            current_module_index=hand.get_current_index(),
            era_name=action_step.era.name if action_step.era is not None else None,
            era_id=action_step.era.pk if action_step.era is not None else None,
            variables=variables,
        )

    @property
    def csv_data(self):
        """Return a dict describing the csv fields that can be deduced from this entity"""
        ret = dict(self["variables"])
        ret.update({"run_started": self["pk"], "action_step_id": self["action_step_id"]})
        return ret


class TeamEntity(FromEntityMixin, datastore.Entity):
    """Ery Datastore Team Entity"""

    def __init__(self, pk, parent, *args, name=None, variables=None, era_name=None, era_id=None, members=None, **kwargs):
        super().__init__(*args, **kwargs)

        self["pk"] = pk

        if name is not None:
            self["name"] = name

        if variables is not None:
            self["variables"] = variables

        if era_name is not None:
            self["era_name"] = era_name

        if era_id is not None:
            self["era_id"] = era_id

        if members is not None:
            self["members"] = members

        if self.key is None:
            self.key = self._make_key(parent=parent)

    def _make_key(self, parent):
        """
        Create a new key for initialization.
        """
        client = get_datastore_client()
        return client.key("Team", self["pk"], parent=parent)

    @staticmethod
    def from_django(team, variables, parent=None, hand=None):
        """
        Create a :class:`TeamEntity` from the Django models.

        Args:
            - team (:class:`~ery_backend.teams.models.Team`)
            - variable_definition (:class:`~ery_backend.variables.models.VariableDefinition`)
            - parent (:class:`google.cloud.datastore.Client.key`): set the entity's datastore ancestor.
            - hand (Optional[:class:`~ery_backend.hands.models.Hand`])

        Returns:
            :class:`TeamEntity`
        """
        entity = TeamEntity(
            pk=team.pk,
            name=team.name,
            members=[hand.pk for hand in team.hands.all()],
            variables=variables,
            era_name=team.era.name,
            era_id=team.era.pk,
            parent=parent,
        )
        return entity

    @property
    def csv_data(self):
        """Return a dict describing the fixed csv fields that can be deduced from this entity"""
        ret = dict(self["variables"])
        ret.update({"team_id": self["pk"], "team_name": self["name"], "team_era": self["era_name"]})
        return ret


class HandEntity(FromEntityMixin, datastore.Entity):
    """Ery Datastore Hand Entity"""

    def __init__(
        self,
        pk,
        parent,
        *args,
        name=None,
        variables=None,
        era_name=None,
        era_id=None,
        current_team=None,
        stage=None,
        frontend=None,
        language=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self["pk"] = pk
        if name is not None:
            self["name"] = name

        if variables is not None:
            self["variables"] = variables

        if era_name is not None:
            self["era_name"] = era_name

        if era_id is not None:
            self["era_id"] = era_id

        if current_team is not None:
            self["current_team"] = current_team

        if stage is not None:
            self["stage"] = stage

        if frontend is not None:
            self["frontend"] = frontend

        if language is not None:
            self["language"] = language

        if self.key is None:
            self.key = self._make_key(parent=parent)

    def _make_key(self, parent):
        """
        Create a new key for initialization.
        """
        client = get_datastore_client()
        return client.key("Hand", self["pk"], parent=parent)

    @staticmethod
    def from_django(hand, variables, parent=None):
        """
        Create a :class:`HandEntity` from the Django models

        Args:
            - hand (:class:`~ery_backend.hands.models.Hand`)
            - variable_definition (:class:`~ery_backend.variables.models.VariableDefinition`)
            - parent (Optional[:class:`google.cloud.datastore.Client.key`]): set the entity's datastore ancestor.

        Returns:
            :class:`HandEntity`
        """
        entity = HandEntity(
            pk=hand.pk,
            name=hand.user.username,
            variables=variables,
            era_name=hand.era.name,
            era_id=hand.era.pk,
            current_team=hand.current_team.name if hand.current_team else None,
            stage=hand.stage.stage_definition.name,
            language=hand.language.name_en,
            frontend=hand.frontend.name,
            parent=parent,
        )

        return entity

    @property
    def csv_data(self):
        """Return a dict describing the fixed csv fields that can be deduced from this entity"""
        ret = dict(self["variables"])
        ret.update(
            {
                "hand_id": self["pk"],
                "hand_name": self["name"],
                "hand_era": self["era_name"],
                "hand_current_team": self["current_team"],
                "hand_stage": self["stage"],
            }
        )
        return ret
