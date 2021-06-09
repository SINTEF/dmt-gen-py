from typing import Dict
from dmt.template_generator import TemplateBasedGenerator

class SetupGenerator(TemplateBasedGenerator):
    """Generate setup file"""

    def generate(self, package_generator, template, outputfile, config: Dict):
        """Generate setup file"""
        model = {}
        model["package_name"] = package_generator.package_name
        model["version"] = config.get("version", "0.0.0")
        model["author"] = config.get("author", "UNKNOWN")
        model["license"] = config.get("license", "UNKNOWN")

        with open(outputfile, 'w', encoding='utf-8') as file:
            file.write(template.render(model))
