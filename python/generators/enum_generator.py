"""blueprint generator"""
import codecs
from pathlib import Path
from typing import Dict
from jinja2.environment import Template
from dmt.common.enum_description import EnumDescription
from dmt.package_generator import PackageGenerator
from dmt import TemplateBasedGenerator
from dmt.common.package import Package


class EnumGenerator(TemplateBasedGenerator):
    """Generate metadata blueprint class"""

    def generate(self, package_generator: PackageGenerator, template: Template, outputfile: Path, config: Dict):
        """Generate metadata blueprint class"""
        outputdir = outputfile.parents[0]
        root_package = package_generator.root_package
        self.__generate_package(root_package,root_package, template, outputdir)

    def __generate_package(self, package: Package,root_package, template, pkg_dir: Path):
        if package is not root_package:
            pkg_dir.mkdir(exist_ok=True)

        for enum in package.enums:
            self.__generate_enum(enum,package,template,pkg_dir)

        for package in package.packages:
            sub_name = package.name
            sub_dir = pkg_dir / sub_name
            self.__generate_package(package,root_package, template, sub_dir)


    def __generate_enum(self, enum: EnumDescription, package: Package, template: Template, outputdir: Path):
        model = self.__create_enum_model(enum)
        model["package_path"]=package.get_path()
        name = model["name"]
        filename = name.lower() + ".py"
        outputfile = outputdir / filename
        outputdir.mkdir(exist_ok=True)

        with codecs.open(outputfile, "w", "utf-8") as file:
            file.write(template.render(model))

    def __create_enum_model(self, enum: EnumDescription):
        model = {}
        name = enum.name
        model["name"] = name
        model["description"] = enum.description
        model["type"] = self.__to_type_string(name)
        model["values"] = enum.enum_values
        return model

    def __to_type_string(self, name: str) -> str:
        return self.first_to_upper(name)
