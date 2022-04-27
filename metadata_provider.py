import os
from pathlib import Path
from typing import Optional, List, Mapping, Type, Set, TypedDict, NamedTuple

from django.db.models import Model
from libcst import BatchableMetadataProvider, Module
from libcst.metadata import FullyQualifiedNameProvider, QualifiedName

from django_type_gen.collect_django import initialize_django


class DeconstructedField(NamedTuple):
    name: str
    path: str
    args: list
    kwargs: dict


class ModelMetadata(TypedDict):
    module: str
    name: str
    abstract: bool
    fields: List[DeconstructedField]


class DjangoMetadataProvider(BatchableMetadataProvider[Mapping[str, List[ModelMetadata]]]):
    METADATA_DEPENDENCIES = (FullyQualifiedNameProvider,)

    @staticmethod
    def gen_cache(
            root_path: Path, paths: List[str], timeout: Optional[int]
    ) -> Mapping[str, object]:
        DJANGO_SETTINGS_MODULE = os.getenv("DJANGO_SETTINGS_MODULE")
        apps, settings = initialize_django(DJANGO_SETTINGS_MODULE)

        models: List[Type[Model]] = apps.get_models()

        models_by_module = {}
        for model in models:
            models_by_module.setdefault(model.__module__, []).append(model)

        return {path: (str(root_path), models_by_module) for path in paths}

    def visit_Module(self, node: "Module") -> Optional[bool]:
        qualified_module: Set[QualifiedName] = self.get_metadata(FullyQualifiedNameProvider, node)
        module = list(qualified_module)[0].name
        root_path, models_by_module = self.cache
        base_module = root_path.replace("/", ".") + "."
        module = module.removeprefix(base_module)
        if module in models_by_module:
            models_in_module = models_by_module[module]
            # models_metadata = []
            # for model_cls in models_in_module:
            #     breakpoint()
            #     models_metadata.append(ModelMetadata(
            #         name=model_cls.__name__,
            #         abstract=model_cls._meta.abstract,
            #         fields=[
            #             field.deconstruct() for field in
            #             model_cls._meta.get_fields() if hasattr(field, "deconstruct")
            #         ],
            #     ))
            self.set_metadata(node, models_in_module)
            return True
        else:
            return False
