#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Code generator for python runtime library
'''

import os
import shutil
from distutils.dir_util import copy_tree
from pathlib import Path
from typing import Dict

from dmt.common.package import Package
from dmt import TemplateBasedGenerator, BaseGenerator

from . import EntityObjectGenerator,InitGenerator,BlueprintGenerator,SetupGenerator,EnumGenerator,PackageInfoGenerator

class RuntimeGenerator(BaseGenerator):
    """ Generates a Python runtime library to access the entities as plain objects """

    def __init__(self,root_dir,package_name,output_dir,root_package: Package) -> None:
        super().__init__(root_dir,package_name,output_dir,root_package)

    def get_template_generators(self) -> Dict[str,TemplateBasedGenerator]:
        """ Override in subclasses """
        return {
            "entity.py.jinja": EntityObjectGenerator(),
            "__init__.py.jinja": InitGenerator(),
            "blueprint.py.jinja": BlueprintGenerator(),
            "setup.py.jinja": SetupGenerator(),
            "enum.py.jinja": EnumGenerator(),
            "package_info.py.jinja": PackageInfoGenerator()
        }

    def copy_templates(self, template_root: Path, output_dir: Path):
        """Copy template folder to output folder"""
        if self.source_only:
            src_dir = template_root / "src"
            dest_dir = output_dir
            copy_tree(str(src_dir), str(dest_dir))
        else:
            copy_tree(str(template_root), str(output_dir))


    def pre_generate(self,output_dir: Path):
        if not self.source_only:
            src_dir = output_dir / "src"
            dest_dir = output_dir / self.package_name
            # rename the src folder to the package name
            if os.path.exists(dest_dir):
                copy_tree(str(src_dir), str(dest_dir))
                shutil.rmtree(src_dir, ignore_errors=True)
            else:
                os.rename(src_dir, output_dir / self.package_name)
