Role-based access control
=========================

Checking permissions
--------------------
The method, has_privilege, found in roles.utils should be used for permissions checking. 
Permissions checking is name based, with names limited to those existing Privilege objects.
In terms of what Alex has said to you concerning CRUD, relevant privileges will be loaded
into the database on initialization via the fixture found in `fixtures/roles_privileges.json`
(assuming that the database is installed with script located at `utility/init_dev_sql.sh`).
These include: "create", "read", "update", "delete", but you will also see ones for 
e.g. "grant", "revoke", "export".

:py:func:`ery_backend.roles.utils.has_privilege` takes an obj (object), user, and name
(a string) as arguments.
Assuming that you already have methods for CRUD in the graphene layer implemented and can import
the has_privilege method, I think you should be able to do as follows:

    - For any class with get_privilege_ancestor, conditionals can be used that implement has_privilege.
        In the case of Action, whose get_privilege_ancestor returns ModuleDefinition
    - Create example code::

        if has_privilege(obj*, user, ‘create’):
            CreateAction.mutate()
            
    - obj should be the object get_privilege_ancestor would point to (in this case the module_definition
        required to create the action)
    - Read, Update, and Delete work in the same way, except with ‘read’, ‘update’, and ‘delete’ as the names of those privileges, respectively.

Note:
    - In the case of Read, for example, even though we’re checking if User has read permissions on Action, the permissions checking is still done on action.get_privilege_ancestor(), which would be a ModuleDefinition.

Testing permissions checking 
----------------------------
In terms of actual testing, you'll need the grant_role method found `roles/utils.py` to actually
assign :py:class:`ery_backend.roles.models.Privilege` to :py:class:`ery_backend.users.models.Users` through
`ery_backend.roles.models.RoleAssignments`. :py:class:`ery_backend.roles.models.Role` is a class in 
`roles/models.py` with a name and set of privileges. These, like privileges, are loaded via the fixture
found in `fixtures/roles_privileges.json` (assuming that the database is installed with script located 
at `utility/init_dev_sql.sh`). Roles include "owner" (all privileges), "viewer" (read privileges), 
"editor" (CRUD privileges), and "administrator" (grant revoke privileges).

RoleAssignments (RoleAssignment found in roles/models.py) assign a Role on a specific object for a user
and/or group. grant_role takes role, obj, (target user and/or group), and optional granter (user that
performed the granting action), and generates a RoleAssignment  for said User and/or Group. As a reminder,
only Stints and Modules (currently only code for ModuleDefinitions is implemented) can be assigned Roles, 
as they are the only topmost ancestors. 


Important notes
---------------
Privileges are inherited from the topmost ancestor, which can be checked using hasattr(get_privilege_ancestor). 

    - Objects that are topmost ancestors, currently only Stints and ModuleDefinitions (only code implemented right now
        is for ModuleDefinition), should not need permission to be created. But permission to edit an action, 
        whose get_privilege_ancestor method ultimately returns the associated ModuleDefinition, would be verified
        by doing has_privilege with said ancestor (ModuleDefinition) as the obj argument.

