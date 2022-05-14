import os
from pathlib import Path
from typing import Optional, List, Mapping, Type, Set, NamedTuple, TYPE_CHECKING, Dict, Tuple

from libcst import BatchableMetadataProvider, Module
from libcst.metadata import FullyQualifiedNameProvider, QualifiedName

from django_type_gen.collect_django import initialize_django


class DeconstructedField(NamedTuple):
    name: str
    path: str
    args: list
    kwargs: dict


ImportDep = Tuple[str, Optional[str]]


class TypeAnnotation(NamedTuple):
    name: str
    annotation: str
    imports_needed: List[ImportDep] = []


class ModelMetadata(NamedTuple):
    module: str
    name: str
    abstract: bool
    annotations: List[TypeAnnotation]
    typing_only_annotations: List[TypeAnnotation]


class DjangoMetadataProvider(BatchableMetadataProvider[Dict[str, List[ModelMetadata]]]):
    METADATA_DEPENDENCIES = (FullyQualifiedNameProvider,)

    @staticmethod
    def gen_cache(
            root_path: Path, paths: List[str], timeout: Optional[int]
    ) -> Mapping[str, object]:
        DJANGO_SETTINGS_MODULE = os.getenv("DJANGO_SETTINGS_MODULE")
        apps, settings = initialize_django(DJANGO_SETTINGS_MODULE)
        from django.db import models
        model_classes: List[Type[models.Model]] = apps.get_models()

        models_by_module = {}
        for model_cls in model_classes:
            models_by_module.setdefault(model_cls.__module__, []).append(model_cls)

        models_metadata_by_module = {}
        for module, models_in_module in models_by_module.items():
            models_metadata = []
            for model_cls in models_in_module:
                annotations = []
                typing_only_annotations = []

                # Add auto-created primary key field
                pk_field = get_primary_key_field(model_cls)
                if pk_field.auto_created:
                    annotations.append(TypeAnnotation(name=pk_field.attname, annotation="int"))

                # Add "_id" fields for ForeignKeys
                for field in model_cls._meta.get_fields(include_parents=False):
                    # See for logic: https://github.com/typeddjango/django-stubs/blob/8fe2bd4b9b6c6b13d893d33eddb12b9118d5aa94/mypy_django_plugin/transformers/models.py#L320

                    # print(field, field.__dict__)
                    if isinstance(field, models.Field):
                        if field.attname != field.name:
                            # TODO: Get actual PK type of field.remote_field
                            field_type = "int"
                            full_field_type = field_type if not field.null else f"Optional[{field_type}]"
                            annotations.append(
                                TypeAnnotation(field.attname, full_field_type, imports_needed=[("typing", "Optional")]))
                            # print(field.attname, field)
                    if isinstance(field, models.ForeignObjectRel):
                        # print(field.name, field.remote_field, field)
                        attname = field.get_accessor_name()
                        if attname is None:
                            # TODO: Also check if name is already defined in class, then it should also be skipped
                            continue
                        if isinstance(field, models.OneToOneRel):
                            # TODO: Technically, if nullable, then the user must check using hasattr.
                            #  But there's no way to represent that afaik
                            typing_only_annotations.append(
                                TypeAnnotation(attname, field.related_model.__qualname__,
                                               [cls_as_import_dep(field.related_model)]))
                        else:
                            # TODO: Generate RelatedManager class derived from related model's manager
                            typing_only_annotations.append(
                                TypeAnnotation(attname, f'RelatedManager[{field.related_model.__qualname__}]',
                                               [('django.db.models.manager', 'RelatedManager'),
                                                cls_as_import_dep(field.related_model)]))

                abstract = model_cls._meta.abstract

                if not abstract:
                    annotations.append(TypeAnnotation(name="pk", annotation="int"))
                models_metadata.append(ModelMetadata(
                    name=model_cls.__name__,
                    module=module,
                    abstract=abstract,
                    annotations=annotations,
                    typing_only_annotations=typing_only_annotations,
                ))
            models_metadata_by_module.setdefault(module, []).extend(models_metadata)

        return {path: (str(root_path), models_metadata_by_module) for path in paths}

    def visit_Module(self, node: "Module") -> Optional[bool]:
        qualified_module: Set[QualifiedName] = self.get_metadata(FullyQualifiedNameProvider, node)
        module = list(qualified_module)[0].name
        root_path, models_metadata_by_module = self.cache
        base_module = root_path.replace("/", ".") + "."
        module = module.removeprefix(base_module)
        if module in models_metadata_by_module:
            models_metadata = models_metadata_by_module[module]
            self.set_metadata(node, models_metadata)
            return True
        else:
            return False


if TYPE_CHECKING:
    from django.db.models import Model, Field


def cls_as_import_dep(cls: Type[object]) -> ImportDep:
    return cls.__module__, cls.__qualname__


def full_qualname(cls: Type[object]) -> str:
    return cls.__module__ + "." + cls.__qualname__


def get_primary_key_field(model_cls: "Type[Model]") -> "Field":
    from django.db.models import Field
    for field in model_cls._meta.get_fields():
        if isinstance(field, Field):
            if field.primary_key:
                return field
    raise ValueError("No primary key defined")
