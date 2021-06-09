"""Generate Python class with properties"""

import codecs
from pathlib import Path
from typing import Dict
from jinja2.environment import Template
from dmt.package_generator import PackageGenerator
from dmt import TemplateBasedGenerator
from dmt.common.package import Package
from .entity_model import create_model

class EntityObjectGenerator(TemplateBasedGenerator):
    """ Generates blueprint test classes"""

    def generate(self, package_generator: PackageGenerator, template: Template, outputfile: Path, config: Dict):
        """Generate blueprint class"""
        outputdir = outputfile.parents[0]
        root_package = package_generator.root_package
        root_name = root_package.name
        package_parent = ""
        self.__generate_package(root_package,root_name, package_parent,template, outputdir)

    def __generate_package(self, package: Package,root_name,package_path, template, pkg_dir):
        for blueprint in package.blueprints:
            self.__generate_entity(blueprint,root_name,package_path,template,pkg_dir)

        for package in package.packages:
            name = package.name
            sub_dir = pkg_dir / name
            self.__generate_package(package,root_name,package_path + "." + name,template, sub_dir)


    def __generate_entity(self, blueprint,root_name,package_path, template: Template, outputdir: Path):
        outputdir.mkdir(exist_ok=True)
        model = create_model(blueprint, root_name,package_path)
        filename = model["name"].lower() + ".py"
        outputfile = outputdir / filename
        with codecs.open(outputfile, "w", "utf-8") as file:
            file.write(template.render(model))
