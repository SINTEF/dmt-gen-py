"""blueprint generator"""
import codecs
import os
from pathlib import Path
from typing import Dict, Sequence
from collections import OrderedDict
from jinja2.environment import Template
from dmtgen.common.package import Blueprint
from dmtgen.package_generator import PackageGenerator
from dmtgen import TemplateBasedGenerator
from dmtgen.common.package import Package
from .entity_model import find_default_value

class BlueprintGenerator(TemplateBasedGenerator):
    """Generate metadata blueprint class"""

    def generate(self, package_generator: PackageGenerator, template: Template, outputfile: Path, config: Dict):
        """Generate metadata blueprint class"""
        outputdir = outputfile.parents[0]
        root_package = package_generator.root_package
        self.__generate_package(root_package,root_package, template, outputdir)

    def __generate_package(self, package: Package,root_package, template, pkg_dir: Path):
        bp_dir = pkg_dir / "blueprints"

        bp_dir.mkdir(exist_ok=True)
        init_file = bp_dir / '__init__.py'
        init_file.touch()

        for blueprint in package.blueprints:
            self.__generate_blueprint(blueprint,root_package,package,template,bp_dir)

        for package in package.packages:
            sub_name = package.name
            sub_dir = pkg_dir / sub_name 
            self.__generate_package(package,root_package, template, sub_dir)


    def __generate_blueprint(self, blueprint: Blueprint,root_package, package: Package, template: Template, outputdir: Path):
        root_name = root_package.name
        model = self.__create_blueprint_model(blueprint,root_name)
        model["package_path"]=package.get_path()
        name = model["name"]
        filename = name.lower() + ".py"
        outputfile = outputdir / filename
        outputdir.mkdir(exist_ok=True)

        with codecs.open(outputfile, "w", "utf-8") as file:
            file.write(template.render(model))

    def __create_blueprint_model(self, blueprint: Blueprint,root_name: str):
        model = {}
        name = blueprint.name
        package = blueprint.get_parent()
        super_classes = self.__find_super_classes(blueprint)
        model["super_classes"] = self.__to__super_classes(super_classes)
        model["name"] = name
        model["imports"] = self.__to__imports(package,super_classes)
        model["root_package"] =root_name
        model["meta_package"] =root_name + ".blueprints"
        model["version"] = 1
        model["description"] = blueprint.description
        model["type"] = self.__to_type_string(blueprint)

        a_dicts = []
        for attribute in blueprint.all_attributes.values():
            a_dict = attribute.as_dict()
            a_dict["is_primitive"] = attribute.is_primitive
            a_dict["optional"] = attribute.optional
            a_dict["is_enum"] = attribute.is_enum
            named_args = []

            if attribute.is_many:
                sdims: str=a_dict["dimensions"]
                dims=sdims.split(",")
                for dim in dims:
                    named_args.append(f'Dimension("{dim.strip()}")')
            if attribute.is_enum:
                a_dict["constructor"]="EnumAttribute"
                a_dict["attributeType"]=root_name+a_dict["enumType"]
            elif attribute.is_primitive:
                if not attribute.optional and not attribute.is_many:
                    named_args.append("optional=False")
                a_dict["constructor"]="Attribute"
                default = find_default_value(attribute)
                if default is not None:
                    named_args.append(f"default={default}")
            else:
                a_dict["contained"]=attribute.contained
                a_dict["constructor"]="BlueprintAttribute"
                atype = a_dict["attributeType"]
                idx = atype.find(":")
                if idx > 0:
                    alias = atype[:idx]
                    adress = package.get_root().aliases[alias]
                    atype = adress + "/" + atype[idx+1:]

                if not atype.startswith("system/SIMOS"):
                    a_dict["attributeType"]=root_name+atype
                else:
                    a_dict["attributeType"]=atype

            if len(named_args) > 0:
                a_dict["named_args"] = ",".join(named_args)

            a_dicts.append(a_dict)

        model["attributes"] = a_dicts



        # dimensions = blueprint.get("dimensions", [])
        dimensions = []
        for dim in dimensions:
            if not "description" in dim:
                dim["description"] = ""
        model["dimensions"] = dimensions
        return model

    def __to_type_string(self, bp: Blueprint) -> str:
        return self.first_to_upper(bp.name)+"Blueprint"

    def __to__super_classes(self, bps: Sequence[Blueprint]) -> str:
        types  = [self.__to_type_string(sc) for sc in bps]
        if types:
            return ",".join(types)
        return "Blueprint"

    def __to__imports(self,package: Package, blueprints: Sequence[Blueprint]) -> Sequence[str]:
        imports = []
        for blueprint in blueprints:
            import_package: Package = blueprint.get_parent()
            if import_package != package:
                relative_path =self._to_relative_import_path(package, blueprint)
                if relative_path.startswith("system.SIMOS"):
                    bp_path = "dmt.blueprints."+ blueprint.name.lower()
                else:
                    bp_path = "." + relative_path + ".blueprints." + blueprint.name.lower()

            else:
                bp_path = "." + blueprint.name.lower()

            bp_name = self.__to_type_string(blueprint)
            imports.append(f"from {bp_path} import {bp_name}")
        return imports

    def __find_super_classes(self, bp: Blueprint) -> Sequence[Blueprint]:
        base_classes: OrderedDict[Blueprint] = OrderedDict()
        for extension in bp.extensions:
            base_classes[extension.name]=extension
        return base_classes.values()

    def _to_relative_import_path(self, pkg: Package, blueprint: Blueprint) -> str:
        import_package = blueprint.get_parent()
        name = blueprint.name.lower()
        if pkg == import_package:
            return "."+name
        current_dir = pkg.package_dir
        import_dir = import_package.package_dir
        import_module = import_package.package_dir / name
        # Get me the relative path from current_dir to import_dir
        root_dir = pkg.get_root().package_dir
        if import_module.is_relative_to(root_dir) and current_dir.is_relative_to(root_dir):
            # Find the relative path from current_dir to import_dir
            relative = os.path.relpath(import_dir, current_dir)
            ret = "".join(Path(relative).parts)
            return ret

        paths = import_package.get_paths()
        return ".".join(paths)
