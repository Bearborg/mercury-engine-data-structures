from typing import Dict, Union, Type

import construct
from construct import Construct, Int32ul, Probe, Struct, Adapter

from mercury_engine_data_structures import hashed_names
from mercury_engine_data_structures.construct_extensions.misc import ErrorWithMessage, ForceQuit
from mercury_engine_data_structures.hashed_names import PropertyEnum


def ConfirmType(name: str):
    def check(ctx):
        return ctx[f"{name}_type"] != name

    return construct.If(
        check,
        ErrorWithMessage(
            lambda ctx: f"Expected {name}, got {ctx[f'{name}_type']} ("
                        f"{hashed_names.all_property_id_to_name().get(ctx[f'{name}_type'])}) "
                        "without assigned type"
        ),
    )


class ObjectAdapter(Adapter):
    def _decode(self, obj: construct.ListContainer, context, path):
        result = construct.Container()
        for item in obj:
            if item.type in result:
                raise construct.ConstructError(f"Type {item.type} found twice in object", path)
            result[item.type] = item.item
        return result

    def _encode(self, obj: construct.Container, context, path):
        return construct.ListContainer(
            construct.Container(
                type=type_,
                item=item
            )
            for type_, item in obj.items()
        )


def Object(fields: Dict[str, Union[Construct, Type[Construct]]], *,
           debug=False) -> Construct:
    all_types = list(fields)
    fields = {
        name: name / conn
        for name, conn in fields.items()
    }

    r = construct.PrefixedArray(
        Int32ul,
        Struct(
            "type" / PropertyEnum,
            "item" / construct.Switch(
                construct.this.type,
                fields,
                ErrorWithMessage(
                    lambda ctx: f"Type {ctx.type} not known, valid types are {all_types}."
                )
            )
        )
    )
    if debug:
        r = construct.FocusedSeq(
            "fields",
            "fields" / r,
            "next_enum" / PropertyEnum,
            "probe" / Probe(lookahead=0x8),
            ForceQuit(),
        )

    return ObjectAdapter(r)
