import builtins
import os
import sys
from contextlib import contextmanager
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from django.apps.registry import Apps  # noqa: F401
    from django.conf import LazySettings  # noqa: F401


@contextmanager
def temp_environ():
    """Allow the ability to set os.environ temporarily"""
    environ = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(environ)


def initialize_django(settings_module: str) -> Tuple["Apps", "LazySettings"]:
    with temp_environ():
        os.environ["DJANGO_SETTINGS_MODULE"] = settings_module

        # add current directory to sys.path
        sys.path.append(os.getcwd())

        def noop_class_getitem(cls, key):
            return cls

        from django.db import models

        models.QuerySet.__class_getitem__ = classmethod(noop_class_getitem)  # type: ignore
        models.Manager.__class_getitem__ = classmethod(noop_class_getitem)  # type: ignore

        # Define mypy builtins, to not cause NameError during setting up Django.
        # TODO: temporary/unpatch
        builtins.reveal_type = lambda _: None
        builtins.reveal_locals = lambda: None

        from django.apps import apps
        from django.conf import settings

        apps.get_models.cache_clear()  # type: ignore
        apps.get_swappable_settings_name.cache_clear()  # type: ignore

        if not settings.configured:
            settings._setup()

        apps.populate(settings.INSTALLED_APPS)

    assert apps.apps_ready
    assert settings.configured

    return apps, settings


# DJANGO_SETTINGS_MODULE = os.getenv("DJANGO_SETTINGS_MODULE")
# apps, settings = initialize_django(DJANGO_SETTINGS_MODULE)
#
# models: List[Type[Model]] = apps.get_models()
# # models = [models[-90]]
#
# models_by_module = {}
# for model in models:
#     models_by_module.setdefault(model.__module__, []).append(model)
#
# for module, models_in_module in models_by_module.items():
#     # f = m._meta.get_fields()[12]
#     # print(f.remote_field.model)
#     py_filename = module.replace(".", "/") + ".py"
#     with open(py_filename) as f:
#         code = f.read()
#     context = CodemodContext(filename=py_filename, full_module_name=module)
#
#     transformer = ModelClassTransformCommand(context, models_in_module=models_in_module)
#     response = transform_module(transformer, code)
#     if isinstance(response, TransformFailure):
#         print(response.error)
#     else:
#         print(diff_code(code, response.code, context=2, filename=py_filename))
#         # print(response.code)
#     # modified_tree = source_tree.visit(transformer)
#     # print(modified_tree.code)
#
# # breakpoint()
