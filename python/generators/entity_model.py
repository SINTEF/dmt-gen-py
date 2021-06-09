import keyword
from collections import OrderedDict
from typing import Dict, Sequence, Set

from dmt.common.blueprint_attribute import BlueprintAttribute
from dmt.common.package import Blueprint, Package

types = {"number": "float", "double": "float", "string": "str", "char": "str",
         "integer": "int", "short": "int", "boolean": "bool"}

default_values = {"float": "0.0", "str": "\"\"", "int": "0", "bool": "False"}

setters = {"float": "float(value)", "str": "str(value)", "int": "int(value)", "bool": "bool(value)"}

def create_model(blueprint: Blueprint, package_name: str, package_path: str):
    model = {}
    name = blueprint.name
    imports = OrderedDict()
    cross_references = OrderedDict()

    model["name"] = name
    model["package"] = package_name
    model["root_package"] = package_name
    model["meta_package"] = package_name + ".blueprints" + package_path
    model["schema_package"] = package_name + ".schema" + package_path +".schemas"
    model["filename"] = name.lower()
    model["version"] = 1
    model["description"] = blueprint.description
    type_name = __first_to_upper(name)
    model["type"] = type_name
    model["blueprint_var_name"] = name.lower()
    model["blueprint_type"] = type_name + "Blueprint"
    model["schema_type"] = type_name + "Schema"

    fields = []
    has_array = False


    for attribute in blueprint.all_attributes.values():
        field = __create_field(attribute,blueprint.parent,imports,cross_references)
        if field:
            fields.append(field)
            if field["is_array"]:
                has_array = True

    model["has_self_reference"] = __refers_to(blueprint, cross_references) or __refers_to(blueprint, imports)
    #Remove any self reference from the imports or cross references
    imports = {name:bp_ref for name, bp_ref in imports.items() if bp_ref != blueprint}
    cross_references = {name:bp_ref for name, bp_ref in cross_references.items() if bp_ref != blueprint}

    model["imports"] = __to__imports(imports.values())
    model["has_cross_references"] = len(cross_references) > 0
    model["cross_references"] = __to__import_infos(cross_references.values())
    model["has_array"] = has_array
    model["fields"] = fields

    # dimensions=blueprint.get("dimensions",[])
    dimensions = []
    model["dimensions"] = dimensions
    # We also create fields to hold the dimensions
    for dim in dimensions:
        field = __create_dimension_field(dim)
        if field:
            fields.append(field)

    return model

def __first_to_upper(string):
    # Make sure the first letter is uppercase
    return string[:1].upper() + string[1:]

def __create_field(attribute: BlueprintAttribute, package: Package,imports: OrderedDict,cross_references: OrderedDict):
    field = {}
    name = __rename_if_reserved(attribute.name)
    field["name"] = name
    dimension = attribute.get("dimensions",None)
    field["description"] = attribute.description
    field["readonly"] = False
    is_array = dimension is not None
    field["is_array"] = is_array
    field["is_cross_reference"]=False
    a_type: str = attribute.get("attributeType")
    if a_type not in types:
        blueprint = package.get_blueprint(a_type)
        if attribute.contained:
            imports[a_type]=blueprint
        else:
            cross_references[a_type]=blueprint
            field["is_cross_reference"]=True

        return __create_blueprint_field(field, blueprint, is_array)

    enum_type = attribute.get("enumType",None)
    if enum_type:
        return __create_enum_field(field,package,enum_type, imports)

    ftype = __map_type(a_type)
    field["is_entity"] = False
    field["type"] = ftype

    if is_array:
        field["type"] = "Sequence["+ftype+"]"
        field["init"] = "list()"
        field["setter"] = "[]"
    else:
        field["setter"] = __map(ftype, setters)
        field["init"] = __find_default_value(attribute, ftype)


    return field

def __rename_if_reserved(name):
    if keyword.iskeyword(name):
        return name + "_"
    return name



def __create_blueprint_field(field, blueprint: Blueprint, is_array) -> Dict:
    field["is_entity"] = True
    import_package: Package = blueprint.get_parent()
    paths=import_package.get_paths()
    bp_path = ".".join(paths) + "." + blueprint.name.lower()
    field["module"] = bp_path
    if is_array:
        field["type"] = "List["+blueprint.name+"]"
        field["simple_type"] = blueprint.name
        field["init"] = "list()"
        field["setter"] = "[]"
    else:
        field["type"] = blueprint.name
        field["setter"] = "value"
        field["init"] = "None"
    return field

def __create_enum_field(field, package: Package, enum_type: str, imports) -> Dict:
    enum = package.get_enum(enum_type)
    imports[enum.name]=enum
    field["type"] = enum.name
    field["setter"] = "value"
    field["init"] = enum.name + "." + enum.default
    return field


def __create_dimension_field(dim):
    field = {}
    field["name"] = dim["name"]
    field["is_array"] = False
    etype = __map_type("integer")
    field["type"] = etype
    field["readonly"] = False
    field["description"] = dim.get("description", "")
    field["init"] = 1
    field["setter"] = "int(value)"
    field["random_value"] = 1
    return field


def __map(key, values):
    converted = values.get(key)
    if not converted:
        raise Exception('Unkown type ' + key)
    return converted


def __map_type(ptype):
    return __map(ptype, types)


def __find_default_value(attribute: BlueprintAttribute, etype: str):
    default_value = attribute.get("default")
    if default_value is not None:
        return __convert_default(attribute,default_value)
    default_value = __map(etype, default_values)
    return default_value


def __convert_default(attribute: BlueprintAttribute, default_value):
    # converts json value to Python value
    if isinstance(default_value,str):
        if default_value == '' or default_value == '""':
            return '""'
        elif attribute.type == 'integer':
            return int(default_value)
        elif attribute.type == 'number':
            return float(default_value)
        elif attribute.type == 'boolean':
            return bool(default_value)
        else:
            return "'" + default_value + "'"
    conversion = {
        "false": "False",
        "true": "True",
    }
    return conversion.get(default_value, default_value)

def __to_type_string(string: str) -> str:
    return string[:1].upper() + string[1:]

def __to__imports(blueprints: Set[Blueprint]) -> Sequence[str]:
    imports = __to__import_infos(blueprints)
    return [__to_import_statement(x) for x in imports]

def __to_import_statement(import_info: Dict) -> str:
    module=import_info["module"]
    name=import_info["name"]
    return f"from {module} import {name}"


def __to__import_infos(blueprints: Set[Blueprint]) -> Sequence[Dict]:
    imports = []
    for blueprint in blueprints:
        import_package: Package = blueprint.get_parent()
        paths=import_package.get_paths()
        name = blueprint.name
        bp_path = ".".join(paths) + "." + name.lower()
        if bp_path == "system.SIMOS.namedentity":
            bp_path = "dmt.named_entity"
        bp_name = __to_type_string(name)
        import_info = {
            "module": bp_path,
            "name": bp_name
        }
        imports.append(import_info)


    return imports

def __refers_to(blueprint: Blueprint, imports: Dict) -> bool:
    return blueprint in imports.values()
    