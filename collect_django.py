# This code is extracted from django-stubs project: https://github.com/typeddjango/django-stubs/
# That project has the following copyright notice:
#
# Copyright (c) Maxim Kurnikov.
# All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

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
        models.ForeignKey.__class_getitem__ = classmethod(noop_class_getitem)  # type: ignore

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
