
from pathlib import Path
from typing import Dict
from jinja2.environment import Template
from dmt.common.package import Blueprint
from dmt.common.package import EnumDescription
from dmt.package_generator import PackageGenerator
from dmt import TemplateBasedGenerator
from dmt.common.package import Package

class InitGenerator(TemplateBasedGenerator):
    """Generate module file for datamodels file"""

    def generate(self, package_generator: PackageGenerator, template: Template, outputfile: Path, config: Dict):
        """Generate blueprint class"""
        outputdir = outputfile.parents[0]
        root_package = package_generator.root_package
        root_name = root_package.name
        file_name = outputfile.name
        package_parent = ""
        self.__generate_package(root_package,root_name, package_parent,template, outputdir,file_name)

    def __generate_package(self, package: Package,root_name,package_path, template, pkg_dir: Path,file_name):
        pkg_dir.mkdir(exist_ok=True)
        blueprints = package.blueprints
        if blueprints:
            model = self.__create_model(package)
            outputfile = pkg_dir / file_name
            with open(outputfile, 'w') as file:
                file.write(template.render(model))

        for package in package.packages:
            name = package.name
            sub_dir = pkg_dir / name
            self.__generate_package(package,root_name,package_path + "." + name,template, sub_dir,file_name)

    def __create_model(self, package:Package):
        """Generate input for Flask route"""
        blueprints = package.blueprints
        model = {}
        model["model_root"] = package.name + ".models"
        types = []
        for blueprint in blueprints:
            types.append(self.__create_type(blueprint))
        for enum in package.enums:
            types.append(self.__create_enum_type(enum))
        model["types"] = types
        return model


    def __create_type(self, blueprint: Blueprint):
        etype = {}
        name = blueprint.name
        etype["path"] = name.lower()
        etype["name"] = self.first_to_upper(name)
        return etype

    def __create_enum_type(self, enum: EnumDescription):
        etype = {}
        name = enum.name
        etype["path"] = name.lower()
        etype["name"] = self.first_to_upper(name)
        return etype
