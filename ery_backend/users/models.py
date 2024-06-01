from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.contrib.postgres.fields import JSONField
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import Group as DjangoGroup
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ery_backend.assets.models import ImageAsset
from ery_backend.base.cache import ery_cache
from ery_backend.base.models import EryModel, EryFileReference
from ery_backend.stints.models import StintDefinition
from ery_backend.modules.models import ModuleDefinition
from ery_backend.templates.models import Template
from ery_backend.themes.models import Theme
from ery_backend.procedures.models import Procedure
from ery_backend.widgets.models import Widget
from ery_backend.validators.models import Validator

from .managers import UserManager


PRIVACY_CHOICES = (
    ('global', _("Global")),
    ('open', _("Open")),
    ('closed', _("Closed")),
)


class Group(DjangoGroup):
    @classmethod
    def get_content_type(cls):
        """Convenience wrapper over django ContentType queryset manager."""
        return ContentType.objects.get_for_model(cls)

    @classmethod
    def get_cache_tag_by_pk(cls, pk):
        """
        Generate cache key for tagging methods to given instance.

        Returns:
            str
        """
        return f"CT:{cls.__name__}:{pk}"

    def get_cache_tag(self):
        return self.get_cache_tag_by_pk(self.pk)

    @classmethod
    def get_cache_key_by_pk(cls, pk):
        """
        Generate representation of instance for use as parameter in other cache keys.

        Returns:
            str
        """
        return f"CK:{cls.__name__}:{pk}"

    def get_cache_key(self):
        return self.get_cache_key_by_pk(self.pk)

    def _invalidate_related_tags(self, history):
        """
        Invalidate cache tags of related models.
        """
        for user in self.user_set.all():
            user.invalidate_tags(history)

    def _invalidate_tag(self):
        """
        Invalidate cache tag.
        """
        from ery_backend.base.cache import invalidate_tag

        invalidate_tag(self.get_cache_tag())

    def invalidate_tags(self, history=None):
        """
        Invalidate own cache tag and those of related models.
        """
        if not history:
            history = [self]
        self._invalidate_tag()
        self._invalidate_related_tags(history)

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Override of default django method, including tag invalidation methods.

        Note: Transactions are declared as atomic (via @transaction.atomic) to ensure commits only occur if all methods
            within save are completed.
        """
        super().save(*args, **kwargs)
        self.invalidate_tags()


class User(AbstractBaseUser):
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['profile']

    objects = UserManager()

    username = models.CharField(
        "username",
        max_length=150,
        unique=True,
        help_text=_("Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."),
        error_messages={'unique': _("A user with that username already exists."),},
    )
    is_active = models.BooleanField(
        "active",
        default=True,
        help_text="Designates whether this user should be treated as active." " Unselect this instead of deleting accounts.",
    )
    is_staff = True  # Required by sites.py in admin
    is_superuser = models.BooleanField(default=False, help_text="Designates whether user should supercede permission system")
    is_creator = models.BooleanField(default=False, help_text="Designates whether user should be allowed to create stints")
    date_joined = models.DateTimeField("date joined", default=timezone.now)
    # Custom group field for use with reversion package
    groups = models.ManyToManyField(
        Group,
        verbose_name="groups",
        blank=True,
        related_name='user_set',
        related_query_name='user',
        help_text="The groups this user belongs to. A user will get all privileges" " granted to each role of their groups.",
    )
    profile = JSONField(
        help_text="Profile information as provided by" " Facebook, Google, Linkedin or edited by user", default=dict
    )
    experience = JSONField(
        help_text="Experience information as provided by" " Facebook, Google, Linkedin or edited by user", default=list
    )
    profile_image = models.ForeignKey('assets.ImageAsset', on_delete=models.SET_NULL, null=True, blank=True)
    followers = models.ManyToManyField(
        "self",
        verbose_name="followers",
        symmetrical=False,
        help_text="The users who are following this user.",
        through='UserRelation',
    )
    privacy = models.CharField(max_length=7, choices=PRIVACY_CHOICES, default='global')
    my_folder = models.ForeignKey('folders.Folder', on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"Username:{self.username}"

    @property
    @ery_cache
    def gql_id(self):
        """Create the expected gql id for a given nodes class name and pk."""
        from ery_backend.base.utils import get_gql_id

        return get_gql_id(f'{self.__class__.__name__}', self.pk)

    @classmethod
    def get_field_name(cls):
        """
        Returns the field name version of the given class.

        Note: Based on assertion that all :class:`EryModel` subclasses are represented
        as ForeignKey fields using the snake casing of their name.
        """
        from ery_backend.base.utils import to_snake_case

        return to_snake_case(cls.__name__)

    # Included for compability with django.contrib.admin
    @staticmethod
    def has_perm(perm, obj=None):
        if settings.DEBUG:
            return True
        return False

    @staticmethod
    def has_module_perms(module):
        if settings.DEBUG:
            return True
        return False

    def get_profile_field(self, field_name):
        authenticators = ('edit', 'facebook', 'google', 'linkedin')

        for authenticator in authenticators:
            if authenticator in self.profile and field_name in self.profile:
                return self.profile[authenticator][field_name]

        # XXX: Until profiles are properly implemented.
        return self.profile.get(field_name)

    @property
    def profile_image_url(self):
        return self.profile_image.filename if self.profile_image else self.get_profile_field('picture')

    @property
    def full_name(self):
        return self.get_profile_field('name')

    @classmethod
    def get_cache_tag_by_pk(cls, pk):
        """
        Generate cache key for tagging methods to given instance.

        Returns:
            str
        """
        return f"CT:{cls.__name__}:{pk}"

    def get_cache_tag(self):
        return self.get_cache_tag_by_pk(self.pk)

    @classmethod
    def get_cache_key_by_pk(cls, pk):
        """
        Generate representation of instance for use as parameter in other cache keys.

        Returns:
            str
        """
        return f"CK:{cls.__name__}:{pk}"

    def get_cache_key(self):
        return self.get_cache_key_by_pk(self.pk)

    @classmethod
    def get_content_type(cls):
        """Convenience wrapper over django ContentType queryset manager."""
        return ContentType.objects.get_for_model(cls)

    @ery_cache(timeout=3)
    def query_library(self):
        model_map = {
            StintDefinition: 'stint_definition',
            ModuleDefinition: 'module_definition',
            Template: 'template',
            Theme: 'theme',
            Procedure: 'procedure',
            Widget: 'widget',
            ImageAsset: 'image_asset',
            Validator: 'validator',
        }
        objs = []
        for model in model_map:
            objs += list(model.objects.filter_privilege('read', self).add_popularity().all())

        objs.sort(key=lambda x: x.popularity, reverse=True)

        return [{model_map[obj.__class__]: obj, 'popularity': obj.popularity, 'owner': obj.get_owner()} for obj in objs]

    def _invalidate_related_tags(self, hisitory):
        """
        Invalidate cache tags of related models.
        """

    def _invalidate_tag(self):
        """
        Invalidate cache tag.
        """
        from ery_backend.base.cache import invalidate_tag

        invalidate_tag(self.get_cache_tag())

    def invalidate_tags(self, history=None):
        """
        Invalidate own cache tag and those of related models.

        Args:
            - history (List[:class:`EryModel`]): Keeps track of which models have already
              had their tags invalidated to prevent circularity.
        """
        if not history:
            history = [self]
        self._invalidate_tag()
        self._invalidate_related_tags(history)

    @transaction.atomic
    def save(self, *args, **kwargs):
        """
        Override of default django method, including tag invalidation methods.

        Note: Transactions are declared as atomic (via @transaction.atomic) to ensure commits only occur if all methods
            within save are completed.
        """
        super().save(*args, **kwargs)
        self.invalidate_tags()


class UserRelation(EryModel):
    from_user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='from_user')
    to_user = models.ForeignKey('User', on_delete=models.CASCADE, related_name='to_user')


class FileTouch(EryFileReference):
    """
    Record user contact with any subclassed ::class::~ery_backend.base.models.EryFileReference
    """

    timestamp = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
