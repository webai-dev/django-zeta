Developer Notes
=======================

On Versioning
-------------
We use Semantic Versioning 2.0.0:
https://semver.org/

Model Creation
--------------

Regarding on_delete
++++++++++++++++++++
*	For models that are shared among users (e.g.,
	:class:`~ery_backend.modules.models.ModuleDefinition`), applying a delete 	   cascade can have catastrophic effects. As such, these models should be protected from deletion so long as they are being shared, and instead have ownership 
	:class:`~ery_backend.roles.models.RoleAssignment` objects removed as desired, with notifications generated to inform users that the current model instance is no longer maintained. Users still using the model are expected to fork 
	(:py:meth:`~ery_backend.base.models.NamedMixin.duplicate`) the deprecated instance.

* 	Attributes referencing related models that do not depend on the model referencing 	  them (e.g., a :class:`~ery_backend.modules.models.ModuleDefinition` with a
	:py:attr:`~ery_backend.modules.models.ModuleDefinition.start_stage`) should be set to null or a default upon deletion. A user should see the consequences of such a delete and be prompted for confirmation before deletion is  executed.

*	All :class:`Language` related attributes should reset to default :class:`Language` 	   of US English on delete.

