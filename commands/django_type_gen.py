from typing import List, Union, Optional

import libcst as cst
from libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst.codemod.visitors import AddImportsVisitor
from libcst.metadata import FullyQualifiedNameProvider

from django_type_gen.metadata_provider import DjangoMetadataProvider, ModelMetadata, ImportDep

AUTO_GENERATED_CODE_START = "# region django-magic-types"
AUTO_GENERATED_CODE_END = "# endregion django-magic-types"


class AddTypesToDjangoModels(VisitorBasedCodemodCommand):
    DESCRIPTION: str = "Add static type annotations to Django models autogenerated based on the Django model registry"

    METADATA_DEPENDENCIES = (FullyQualifiedNameProvider, DjangoMetadataProvider)

    def __init__(self, context: CodemodContext):
        super().__init__(context)
        self.indent_depth = 0
        self.in_class_name = []

    def visit_Module(self, node: cst.Module) -> Optional[bool]:
        self.models_metadata: List[ModelMetadata] = self.get_metadata(DjangoMetadataProvider, node, [])
        return True

    def visit_IndentedBlock(self, node: cst.IndentedBlock) -> None:
        self.indent_depth += 1

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        self.in_class_name.append(node.name.value)

    def leave_ClassDef(
            self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> Union[cst.BaseStatement, cst.FlattenSentinel[cst.BaseStatement], cst.RemovalSentinel]:
        self.in_class_name.pop()
        return updated_node

    def add_imports(self, imports_needed: List[ImportDep]):
        for imp in imports_needed:
            AddImportsVisitor.add_needed_import(
                self.context, imp[0], imp[1]
            )

    def leave_IndentedBlock(
            self, original_node: cst.IndentedBlock, updated_node: cst.IndentedBlock
    ) -> cst.BaseSuite:
        self.indent_depth -= 1
        if self.indent_depth != 0:
            return original_node
        if len(self.in_class_name) != 1:
            return original_node
        class_name = self.in_class_name[0]
        model_metadata = next((m for m in self.models_metadata if m.name == class_name), None)

        if not model_metadata:
            return original_node

        modified_body = []
        original_body = updated_node.body

        # Remove any existing auto-generated regions
        in_autogenerated_region = False
        for node in original_body:
            if hasattr(node, "leading_lines") and node.leading_lines:
                if node.leading_lines[0].comment:
                    if node.leading_lines[0].comment.value == AUTO_GENERATED_CODE_END:
                        new_leading_lines = list(node.leading_lines)
                        # Remove comment
                        new_leading_lines.pop(0)
                        # Remove empty line
                        new_leading_lines.pop(0)
                        node = node.with_changes(leading_lines=new_leading_lines)
                        in_autogenerated_region = False
                    elif node.leading_lines[0].comment.value == AUTO_GENERATED_CODE_START:
                        in_autogenerated_region = True
                        continue
            if isinstance(node, cst.EmptyLine) and node.comment:
                if node.comment.value == AUTO_GENERATED_CODE_START:
                    in_autogenerated_region = True
                    continue
                elif node.comment.value == AUTO_GENERATED_CODE_END:
                    in_autogenerated_region = False
                    continue
            if not in_autogenerated_region:
                modified_body.append(node)


        # TODO: If attr already exists, don't add it
        # TODO: Add proper imports if necessary
        # TODO: Use proper type
        # AddImportsVisitor.add_needed_import(
        #     self.context, "typing", "TYPE_CHECKING",
        # )

        generated_body = [cst.EmptyLine(comment=cst.Comment(value=AUTO_GENERATED_CODE_START)), cst.EmptyLine()]

        for annotation in model_metadata.annotations:
            statement = cst.parse_statement(f"{annotation.name}: {annotation.annotation}")
            for imp in annotation.imports_needed:
                generated_body.append(cst.parse_statement(f"from {imp[0]} import {imp[1]}"))
            generated_body.append(statement)
        if model_metadata.typing_only_annotations:
            typing_only_statements = []
            for ann in model_metadata.typing_only_annotations:
                for imp in ann.imports_needed:
                    typing_only_statements.append(f"from {imp[0]} import {imp[1]}")
            typing_only_statements = sorted(set(typing_only_statements))
            typing_only_statements.extend([f"{annotation.name}: {annotation.annotation}" for annotation in
                                      model_metadata.typing_only_annotations])
            generated_body.append(cst.parse_statement('from typing import TYPE_CHECKING'))
            statement = cst.parse_statement("\n".join([f"if TYPE_CHECKING:", *["\t" + statement for statement in typing_only_statements]]))
            generated_body.append(statement)

        generated_body.append(cst.EmptyLine(comment=cst.Comment(value=AUTO_GENERATED_CODE_END)))
        generated_body.append(cst.EmptyLine())
        return updated_node.with_changes(body=[*generated_body, *modified_body])
