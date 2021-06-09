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
    super_classes = __find_super_classes(blueprint)
    model["super_classes"] = __to__super_classes(super_classes)
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
    # We should also check that the imports does not point to this as a cross ref.
    #Remove any self reference from the imports or cross references

    imports = {name:bp_ref for name, bp_ref in imports.items() if bp_ref != blueprint}
    cross_references = {name:bp_ref for name, bp_ref in cross_references.items() if bp_ref != blueprint}

    import_types= set(imports.values())
    import_types = import_types.union(super_classes)

    pkg=blueprint.get_parent()
    for import_type in imports.values():
        if isinstance(import_type, Blueprint):
            for attribute  in import_type.all_attributes.values():
                if not attribute.is_primitive and not attribute.is_enum:
                    imp_bp = pkg.get_blueprint(attribute.type)
                    if blueprint == imp_bp:
                        cross_references[import_type.name] = import_type
                        import_types.remove(import_type)

    model["imports"] = __to__imports(import_types)
    model["has_cross_references"] = len(cross_references) > 0
    model["cross_references"] = __to__import_infos(cross_references.values())
    model["has_array"] = has_array
    model["fields"] = fields
    model["arguments"]=__create_named_arguments(fields)
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
    a_type: str = attribute.get("attributeType")
    if a_type not in types:
        blueprint = package.get_blueprint(a_type)
        if attribute.contained:
            imports[a_type]=blueprint
        else:
            cross_references[a_type]=blueprint
        return __create_blueprint_field(field, blueprint, is_array, attribute)

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
        field["default"] = __find_default_value(attribute, ftype)
        field["init"] = field["default"]


    return field

def __rename_if_reserved(name):
    if keyword.iskeyword(name):
        return name + "_"
    return name



def __create_blueprint_field(field, blueprint: Blueprint, is_array, attribute: BlueprintAttribute) -> Dict:
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
        optional = attribute.get("optional",True)
        if attribute.contained and not optional and not blueprint.abstract:
            # Then we create an inital
            field["init"] = blueprint.name + "()"
    return field

def __create_enum_field(field, package: Package, enum_type: str, imports) -> Dict:
    enum = package.get_enum(enum_type)
    imports[enum.name]=enum
    field["is_entity"] = False
    field["type"] = enum.name
    field["setter"] = "value"
    field["init"] = enum.name + "." + enum.default
    return field

def __map(key, values):
    converted = values.get(key)
    if not converted:
        raise Exception('Unkown type ' + key)
    return converted


def __map_type(ptype):
    return __map(ptype, types)


def find_default_value(attribute: BlueprintAttribute):
    """Returns the default value literal"""
    a_type: str = attribute.get("attributeType")
    etype = __map_type(a_type)
    default_value = attribute.get("default")
    if default_value is not None:
        return __convert_default(attribute,default_value)
    default_value = __map(etype, default_values)
    return default_value

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
    statements = [__to_import_statement(x) for x in imports]
    statements.sort()
    return statements

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

def __create_named_arguments(fields: Sequence[Dict]) -> str:
    args = []
    for field in fields:
        if not field["is_entity"] and not field["is_array"]:
            default_value = field["init"]
            name = field["name"]
            args.append(name + ":" + field["type"] +"="+ str(default_value))
            field["init"] = name

    if len(args) == 0:
        return ""

    return ", " + ", ".join(args)

def __find_super_classes(blueprint: Blueprint) -> Sequence[Blueprint]:
    base_classes: OrderedDict = OrderedDict()
    for extension in blueprint.extensions:
        if extension.name != "NamedEntity":
            base_classes[extension.name]=extension
    return base_classes.values()

def __to__super_classes(bps: Sequence[Blueprint]) -> str:
    types  = [__to_type_string(bp.name) for bp in bps]
    if types:
        return ",".join(types)
    return "Entity"
