from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

import reversion

from ery_backend.users.models import User, Group
from ..base.models import EryModel, EryNamedPrivileged


@reversion.register()
class Privilege(EryNamedPrivileged):
    # Name of privileges should be read-only due to name-based caching
    def _invalidate_related_tags(self, history):
        """
        Invalidate cache tags of related models.
        """
        for role in self.role_set.all():
            role.invalidate_tags(history)


class RoleParent(EryModel):
    role = models.ForeignKey('roles.Role', on_delete=models.CASCADE)
    parent = models.ForeignKey('roles.Role', related_name='roleparent_parent', on_delete=models.CASCADE)

    def clean(self):
        if self.role == self.parent:
            raise ValidationError(
                {
                    'parent': 'Cannot assign parent: {} (id: {}). It is the same as the role: {} (id: {}),'
                    ' it is being assigned to.'.format(self.role, self.role.id, self.parent, self.parent.id)
                }
            )

    def post_save_clean(self):
        """
        Since circularity checks require current RoleParent have an id, they must be done post_save
        """
        result, result_info = self.parent._is_circular()  # pylint: disable=protected-access
        if result:
            self.delete()
            raise ValidationError(
                {
                    'parent': 'Cannot assign parent. Adding the current role: {} (id: {}), as a parent to role: {} (id: {}),'
                    ' would cause a circular reference, where {} (id: {}) eventually'
                    ' has itself as an ancestor'.format(
                        self.parent, self.parent.id, self.role, self.role.id, result_info['role'], result_info['role'].id
                    )
                }
            )

    def _invalidate_related_tags(self, history):
        """
        Invalidate cache tags of related models.
        """
        self.role.invalidate_tags(history)


@reversion.register()
class Role(EryNamedPrivileged):
    parents = models.ManyToManyField('Role', through='roles.RoleParent')
    privileges = models.ManyToManyField(Privilege, blank=True)

    def has_privilege(self, privilege_name):
        """
        Check if role directly or indirectly owns :class:`Privilege` of given name.

        Notes:
            - Indirect ownership occurs when a parent (grandparent, etc) owns said :class:`Privilege`.
        """
        if self.privileges.filter(name=privilege_name).exists():
            return True
        for parent in self.parents.all():
            if parent.has_privilege(privilege_name):
                return True
        return False

    def _is_circular(self, roles=None):
        if not roles:
            roles = [self]
        else:
            if self in roles:  # Current role is already part of chain of RoleParents, indicating circularity
                return True, {'role': self}
            roles.append(self)
        # Follow each parent in role.parents upwards to check for circularity
        for parent in self.parents.all():
            result, result_info = parent._is_circular(roles)  # pylint: disable=protected-access
            if result:
                return result, result_info
        return False, None

    def get_descendant_ids(self):
        role_ids = set(self.role_set.values_list('id', flat=True))
        for child in self.role_set.all():
            role_ids.update(child.get_descendant_ids())

        return role_ids

    def _get_inherited_privilege_ids(self):
        privilege_id_set = set()
        for parent in self.parents.all():
            privilege_id_set.update(parent.get_all_privilege_ids())
        return privilege_id_set

    def get_all_privilege_ids(self):
        # Add immediate privilege ids
        privilege_id_set = set(self.privileges.values_list('id', flat=True))
        # Add privilege ids of parents and their ancestors
        privilege_id_set.update(self._get_inherited_privilege_ids())

        return privilege_id_set

    def _invalidate_related_tags(self, history):
        """
        Invalidate cache tags of related models.
        """
        for role_parent in self.roleparent_set.all():
            if role_parent not in history:
                history.append(role_parent)
                role_parent.parent.invalidate_tags(history)

    def invalidate_tags(self, history=None):
        if not history:
            history = [self]
        self._invalidate_tag()
        self._invalidate_related_tags(history)


@reversion.register()
class RoleAssignment(EryModel):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    obj = GenericForeignKey()
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        assignee = self.user if self.user else self.group
        return "RoleAssignment: {} has {} on {}".format(assignee, self.role, self.obj)

    def clean(self):
        super().clean()
        if self.user and self.group:
            raise ValidationError("Can not specify both user and group.")
        if not self.user and not self.group:
            raise ValidationError("Either user or group is mandatory.")

    def _invalidate_related_tags(self, history):
        """
        Invalidate cache tags of related models.
        """
        if self.user:
            self.user.invalidate_tags(history)
        else:
            self.group.invalidate_tags(history)
