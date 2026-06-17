import keyword
from collections import OrderedDict
from typing import Dict, Sequence, Set

from .common import to_safe_string

from dmtgen.common.blueprint_attribute import BlueprintAttribute
from dmtgen.common.package import Blueprint, Package

types = {"number": "float", "double": "float", "string": "str", "char": "str",
         "integer": "int", "short": "int", "boolean": "bool"}

default_values = {"float": 0.0, "str": None, "int": 0, "bool": False}

setters = {"float": "float(value)", "str": "value", "int": "int(value)", "bool": "bool(value)"}

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
    model["description"] = to_safe_string(blueprint.description)
    type_name = __first_to_upper(name)
    model["type"] = type_name
    model["blueprint_var_name"] = name.lower()
    model["blueprint_type"] = type_name + "Blueprint"
    model["schema_type"] = type_name + "Schema"

    fields = []
    has_array = False
    needs_numpy = False


    for attribute in blueprint.all_attributes.values():
        # _id is the runtime-managed entity UUID, not a model field.
        if attribute.name == "_id":
            continue
        field = __create_field(attribute,blueprint.parent,imports,cross_references)
        if field:
            fields.append(field)
            if field["is_array"]:
                has_array = True
                needs_numpy |= not field["is_entity"]

    model["has_self_reference"] = __refers_to(blueprint, cross_references) or __refers_to(blueprint, imports)
    # We should also check that the imports does not point to this as a cross ref.
    #Remove any self reference from the imports or cross references

    imports = {name:bp_ref for name, bp_ref in imports.items() if bp_ref != blueprint}
    cross_references = {name:bp_ref for name, bp_ref in cross_references.items() if bp_ref != blueprint}

    import_types= set(imports.values())
    import_types = import_types.union(super_classes)

    pkg=blueprint.parent
    for import_type in imports.values():
        if isinstance(import_type, Blueprint):
            for attribute  in import_type.all_attributes.values():
                if not attribute.is_primitive and not attribute.is_enum():
                    imp_bp = pkg.get_blueprint(__anchor_subpackage_path(pkg, attribute.type))
                    if blueprint == imp_bp:
                        cross_references[import_type.name] = import_type
                        import_types.remove(import_type)

    model["imports"] = __to__imports(pkg,import_types)
    model["has_cross_references"] = len(cross_references) > 0
    model["cross_references"] = __to__import_infos(pkg,cross_references.values())
    model["has_array"] = has_array
    model["needs_numpy"] = needs_numpy
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
    field["description"] = to_safe_string(attribute.description)
    field["readonly"] = False
    is_array = dimension is not None

    field["is_array"] = is_array
    a_type: str = attribute.type
    if a_type not in types:
        bp_parent = attribute.parent
        bp_package = bp_parent.parent
        blueprint = bp_package.get_blueprint(__anchor_subpackage_path(bp_package, a_type))
        if attribute.contained:
            imports[a_type]=blueprint
        else:
            cross_references[a_type]=blueprint
        return __create_blueprint_field(field, blueprint, is_array)

    if attribute.is_enum():
        return __create_enum_field(field,attribute,package,attribute.enum_type, imports)

    ftype = __map_type(a_type)
    field["is_entity"] = False
    field["type"] = ftype
    field["type_description"] = ftype

    if is_array:
        dims=dimension.split(",")
        field["type"] = "ndarray"
        field["type_description"] = "ndarray of " + ftype
        field["ftype"] = ftype
        field["init"] = "[]"
        field["setter"] = f"asarray(value, dtype={ftype})"
        field["ndim"] = len(dims)

    else:
        field["setter"] = __map(ftype, setters)
        field["default"] = __find_default_value(attribute, ftype)
        field["init"] = field["default"]

    return field

def __anchor_subpackage_path(package: Package, a_type: str) -> str:
    # Re-anchor a root-relative "/sub/Type" ref under the root package name.
    if a_type.startswith("/"):
        return "/" + package.get_root().name + a_type
    return a_type

def __rename_if_reserved(name):
    if keyword.iskeyword(name):
        return name + "_"
    return name



def __create_blueprint_field(field, blueprint: Blueprint, is_array) -> Dict:
    field["is_entity"] = True
    import_package: Package = blueprint.parent
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

def __create_enum_field(field,attribute: BlueprintAttribute, package: Package, enum_type: str, imports) -> Dict:
    enum = package.get_enum(enum_type)
    imports[enum.name]=enum
    field["is_entity"] = False
    field["type"] = enum.name
    field["setter"] = "value"
    init=attribute.content.get("default",enum.default)
    field["init"] = enum.name + "." +init
    return field

def __map(key, values):
    converted = values.get(key)
    if not converted:
        raise ValueError('Unkown type ' + key)
    return converted


def __map_type(ptype):
    return __map(ptype, types)


def find_default_value(attribute: BlueprintAttribute):
    """Returns the default value literal"""
    a_type: str = attribute.get("attributeType")
    etype = __map_type(a_type)
    return __find_default_value(attribute, etype)

def __find_default_value(attribute: BlueprintAttribute, etype: str):
    default_value = attribute.get("default")
    if default_value is not None:
        return __convert_default(attribute,default_value)
    return default_values[etype]


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
            return default_value.lower() == "true"
        else:
            return "'" + default_value + "'"
    return default_value

def __to_type_string(string: str) -> str:
    return string[:1].upper() + string[1:]

def __to__imports(pkg: Package,  blueprints: Set[Blueprint]) -> Sequence[str]:
    imports = __to__import_infos(pkg, blueprints)
    statements = [__to_import_statement(x) for x in imports]
    statements.sort()
    return statements

def __to_import_statement(import_info: Dict) -> str:
    module=import_info["module"]
    name=import_info["name"]
    return f"from {module} import {name}"


def __to__import_infos(pkg: Package,blueprints: Set[Blueprint]) -> Sequence[Dict]:
    imports = []
    for blueprint in blueprints:
        bp_path=_to_relative_import_path(pkg,blueprint)
        name = blueprint.name
        if bp_path.startswith("system.SIMOS"):
            bp_path = "dmt."+ name.lower()
        bp_name = __to_type_string(name)
        import_info = {
            "module": bp_path,
            "name": bp_name
        }
        imports.append(import_info)

    return imports

def _to_relative_import_path(pkg: Package, blueprint: Blueprint) -> str:
    import_package = blueprint.parent
    name = blueprint.name.lower()

    pkg_paths = pkg.get_paths()
    import_paths = import_package.get_paths()
    # Relative import only when both share a root package; else absolute.
    if pkg_paths[0] == import_paths[0]:
        common = 0
        for own, other in zip(pkg_paths, import_paths):
            if own != other:
                break
            common += 1
        ups = len(pkg_paths) - common
        descent = import_paths[common:]
        dots = "." * (ups + 1)
        if ups == 0:
            return dots + ".".join(descent + [name])
        if descent:
            # Into a sibling subpackage: import the package, rely on __init__.
            return dots + ".".join(descent)
        # Ancestor ref: import the module directly to avoid a circular import.
        return dots + name

    return ".".join(import_paths)

def __refers_to(blueprint: Blueprint, imports: Dict) -> bool:
    return blueprint in imports.values()

def __create_named_arguments(fields: Sequence[Dict]) -> str:
    args = []
    for field in fields:
        if not field["is_entity"] and not field["is_array"]:
            default_value = field["init"]
            if default_value is not None:
                name = field["name"]
                args.append(name  + "="+ str(default_value))
                field["init"] = name

    if len(args) == 0:
        return ""

    return ", " + ", ".join(args)

def __find_super_classes(blueprint: Blueprint) -> Sequence[Blueprint]:
    base_classes: OrderedDict = OrderedDict()
    for extension in blueprint.extensions:
            base_classes[extension.name]=extension
    return base_classes.values()

def __to__super_classes(bps: Sequence[Blueprint]) -> str:
    types  = [__to_type_string(bp.name) for bp in bps]
    if types:
        return ",".join(types)
    return "Entity"
