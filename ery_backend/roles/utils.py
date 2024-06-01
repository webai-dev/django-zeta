import logging

from django.core.exceptions import ObjectDoesNotExist

import reversion

from ery_backend.base.cache import invalidate_tag, ery_cache, tag_key
from ery_backend.base.models import EryFile
from ery_backend.base.exceptions import EryTypeError
from ery_backend.users.models import User, Group

from .models import Role, RoleAssignment, Privilege


logger = logging.getLogger(__name__)


def _log_role_update(logger_level_func, action, role, obj, user=None, group=None, updater=None):
    """
    Logging function for changes in permissions
    """
    msg_start = "User '{}' {}".format(updater, action) if updater else action.capitalize()
    msg_to = "with {} '{}'".format("user" if user else "group", user if user else group)
    logger_level_func("{} role '{}' {} on '{}'".format(msg_start, role, msg_to, obj))


def _validate_arguments(action, role, obj, user, group, updater):
    msg_start = "Failed to {} role.".format(action)

    if not isinstance(role, Role):
        raise EryTypeError("{} First argument needs to be instance of {}".format(msg_start, Role))
    if not obj:
        raise EryTypeError("{} Second argument can't be of type {}".format(msg_start, type(None)))
    if group and not isinstance(group, Group):
        raise EryTypeError("{} The 'group=' argument needs to be instance of {}".format(msg_start, Group))
    if user and not isinstance(user, User):
        raise EryTypeError("{} The 'user=' argument needs to be instance of {}".format(msg_start, User))
    if user is None and group is None:
        raise EryTypeError("{} Passing either the 'user=' or 'group=' argument is mandatory".format(msg_start))
    if updater and not isinstance(updater, User):
        raise EryTypeError("{} The '{}er=' argument needs to be instance of {}".format(msg_start, action, User))


def grant_role(role, obj, user=None, group=None, granter=None):
    """
    Creates a role assignment for a role and an obj and assigns to user or group, with the option
    of recording who granted said role.
    Note: Invalidates all cache keys invalidated by the addition of a new role assignment

    Returns:
        :class:`~ery_backend.roles.utils.RoleAssignment`
    """
    _validate_arguments("grant", role, obj, user, group, granter)
    role_assignment = None
    if hasattr(obj, 'parent_field') and obj.parent_field:
        raise EryTypeError(
            'A role can only be granted to privilege ancestor objects. {} is a descendant. '
            'its privilege ancestor, {}, must be used instead.'.format(obj.__class__, obj.get_privilege_ancestor().__class__)
        )

    tags = [role.get_cache_tag()]
    # Invalidate all cache keys of has_privilege associated to privileges in current role by invalidating privilege key
    privilege_ids = role.get_all_privilege_ids()
    privilege_set = Privilege.objects.filter(id__in=privilege_ids)
    for privilege in privilege_set.all():
        tags.append(privilege.get_cache_tag())  # Removed related func:has_privilege keys from cache

    if not RoleAssignment.objects.filter(
        role=role, object_id=obj.id, content_type=obj.get_content_type(), user=user, group=group
    ).exists():

        with reversion.create_revision():
            role_assignment = RoleAssignment.objects.create(
                role=role, object_id=obj.id, content_type=obj.get_content_type(), user=user, group=group
            )
            reversion.set_comment("Grant role")
            if granter:
                reversion.set_user(granter)
        _log_role_update(logger.info, "granted", role, obj, user, group, granter)
    else:
        _log_role_update(logger.debug, "tried to grant already granted", role, obj, user, group, granter)

    for tag in tags:
        invalidate_tag(tag)
    return role_assignment


def grant_ownership(obj, user=None, group=None, granter=None):
    ownership = Role.objects.get(name="owner")
    return grant_role(ownership, obj, user=user, group=group, granter=granter)


def revoke_role(role, obj, user=None, group=None, revoker=None):
    """
    Removes role assignment for a role and an obj belonging to user (if specified) or group (if specified)
    with the option of recording who revoked said role.
    Note: Invalidates all cache keys invalidated by the removal of role assignments
    """
    _validate_arguments("revoke", role, obj, user, group, revoker)
    if obj.parent_field:
        raise EryTypeError(
            'A role can only be revoked from stint and module objects. {} is a descendant. '
            'its privilege ancestor, {}, must be used instead.'.format(obj.__class__, obj.get_privilege_ancestor().__class__)
        )

    tags = []
    role_assignment_qs = RoleAssignment.objects.filter(
        role=role, object_id=obj.id, content_type=obj.get_content_type(), user=user, group=group
    )
    if role_assignment_qs:
        # Invalidate all cache keys of has_privilege associated to privileges in current role by invalidating privilege key
        privilege_ids = role.get_all_privilege_ids()
        privilege_set = Privilege.objects.filter(id__in=privilege_ids)
        for privilege in privilege_set.all():
            tags.append(privilege.get_cache_tag())  # Removed related func:has_privilege keys from cache

        with reversion.create_revision():
            for role_assignment in role_assignment_qs.all():
                role_assignment.delete()
            reversion.set_comment("Revoke role")
            if revoker:
                reversion.set_user(revoker)
        _log_role_update(logger.info, "revoked", role, obj, user, group, revoker)
    else:
        _log_role_update(logger.debug, "tried to revoke non-existent", role, obj, user, group, revoker)

    for tag in tags:
        invalidate_tag(tag)


def _get_privilege_obj(obj):
    if hasattr(obj, "get_privilege_ancestor"):
        return obj.get_privilege_ancestor()
    return obj


@ery_cache
def _get_privilege(privilege_name):
    try:
        privilege = Privilege.objects.get(name=privilege_name)
    except Privilege.DoesNotExist:
        raise ObjectDoesNotExist('Privilege {}: Does Not Exist'.format(privilege_name))

    cache_key = _get_privilege.cache_key(privilege_name)
    tag_key(privilege.get_cache_tag(), cache_key)

    return privilege


def has_privilege(obj, user, privilege_name):
    """
    Actions:
        - Check that role exists for user and object such that role definition includes privilege
        - Defaults to cached values if they exist

    Note:
        Cached keys are invalidated if privilege key or role key is invalidated
    """
    if not obj:
        raise EryTypeError("Failed to search for matching privileges." "First argument can't be of type None")
    if not isinstance(user, User):
        raise EryTypeError("Failed to search for matching privileges." "Second argument needs to be of type User.")
    if not isinstance(privilege_name, str):
        raise EryTypeError("Failed to search for matching privileges." "Third argument needs to be of type str.")

    if user.is_superuser:
        return True

    if privilege_name == 'read' and isinstance(obj, EryFile) and obj.published:
        return True

    result = False

    privilege = _get_privilege(privilege_name)
    privilege_obj = _get_privilege_obj(obj)
    tags = set((privilege.get_cache_tag(),))  # Tag result to privilege cache_key

    # Filter assignments of same class model for privilege
    role_assignment_qs = RoleAssignment.objects.filter(
        content_type=privilege_obj.get_content_type(), object_id=privilege_obj.id
    )

    # Check if any assignments belong to user
    for role_assignment in role_assignment_qs.filter(user=user).select_related('role'):
        if role_assignment.role.has_privilege(privilege_name):
            result = True
            tag = role_assignment.role.get_cache_tag()
            tags.add(tag)
            # Results should be invalidated if role tag is invalidated
            break

    if result is False:
        # Check if any assignments belong to user's groups
        for group in user.groups.all():
            for role_assignment in role_assignment_qs.filter(group=group).select_related('role'):
                if role_assignment.role.has_privilege(privilege_name):
                    result = True
                    tag = role_assignment.role.get_cache_tag()
                    tags.add(tag)
                    break

    # XXX: Address in issue #783
    # cache_key = has_privilege.cache_key(obj, user, privilege_name)
    # tag_key(tags, cache_key)

    return result


def get_cached_role_ids_by_privilege(privilege_name):
    """
    1) Returns list of ids of all roles and children of roles containing privilege identified by
    privilege name
    2) Defaults to cached values if they exist
    Notes:
        - Keys are invalidated when any role the privilege has been tagged to or the privilege itself  is modified
    """
    privilege = _get_privilege(privilege_name)
    # Only direct ownership is measured. If a role indirectly has a privilege, confirmation should be done on the
    # parent containing said privilege through the role's has_privilege method.
    query = Role.objects.filter(privileges__in=[privilege])
    role_ids = set(query.values_list('id', flat=True))
    for role in query.all():
        role_ids.update(role.get_descendant_ids())

    # Connect results to each relevant role by tagging privilege cache tag to role cache_keys
    tags = [privilege.get_cache_tag()]
    tags += [role.get_cache_tag() for role in query.all()]

    # XXX: Address in issue #783
    # cache_key = get_cached_role_ids_by_privilege.cache_key(privilege_name)
    # tag_key(tags, cache_key)
    return list(role_ids)


def get_role_objs():
    """
    Objects that can be assigned a :class:`~ery_backend.roles.models.Role`.
    """
    from ery_backend.assets.models import ImageAsset
    from ery_backend.folders.models import Folder
    from ery_backend.labs.models import Lab
    from ery_backend.modules.models import ModuleDefinition
    from ery_backend.procedures.models import Procedure
    from ery_backend.stint_specifications.models import StintSpecification
    from ery_backend.stints.models import StintDefinition
    from ery_backend.templates.models import Template
    from ery_backend.themes.models import Theme
    from ery_backend.validators.models import Validator
    from ery_backend.widgets.models import Widget

    return {
        'ImageAsset': ImageAsset,
        'Folder': Folder,
        'Lab': Lab,
        'ModuleDefinition': ModuleDefinition,
        'Procedure': Procedure,
        'StintSpecification': StintSpecification,
        'StintDefinition': StintDefinition,
        'Template': Template,
        'Theme': Theme,
        'Validator': Validator,
        'Widget': Widget,
        'Role': Role,
        'Privilege': Privilege,
    }
