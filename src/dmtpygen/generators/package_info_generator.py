"""Generate Python class with properties"""

import codecs
import json
from pathlib import Path
from typing import Dict, Sequence
from jinja2.environment import Template

from dmtgen import TemplateBasedGenerator
from dmtgen.package_generator import PackageGenerator
from dmtgen.common.package import Package


class PackageInfoGenerator(TemplateBasedGenerator):
    """ Generates blueprint test classes"""

    def generate(self, package_generator: PackageGenerator, template: Template, outputfile: Path, config: Dict):
        model  = {}
        package = package_generator.root_package
        model["version"] = package.version
        model["packages"] = self.__create_package_infos(package)
        with codecs.open(outputfile, "w", "utf-8") as file:
            file.write(template.render(model))

    def __create_package_infos(self, pkg: Package) -> Sequence[Dict]:
        pinfos = {}
        for package in pkg.packages:
            pinfos[package.name]=self.__package_version(package)
        return pinfos

    def __package_version(self, package: Package) -> int:
        version = package.version
        if version is not None:
            return int(version)
        # Fall back to the version file when the package version is unset.
        versions_file = package.package_dir / "__versions__.json"
        if versions_file.exists():
            versions = json.loads(versions_file.read_text(encoding="utf-8"))
            version = versions.get(package.name)
            if version is not None:
                return int(version)
        return 0
