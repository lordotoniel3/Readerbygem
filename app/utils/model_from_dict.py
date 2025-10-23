from datetime import datetime
from typing import Type, TypeVar, get_args

from sqlmodel import SQLModel

from app.utils.safe_parse import safe_parse_int, safe_parse_date, safe_parse_float, safe_parse_str


def _unwrap_optional(tp) -> Type:
    """Unwrap Optional[X] or X | None to X"""
    args = get_args(tp)
    if args:
        return args[0]
    return tp


T = TypeVar("T", bound=SQLModel)
def map_model_from_dict(model: Type[T], d: dict) -> T | None:
    """
    Little utility function to automatically map fields from a dict
    and depending on the type safe parse them
    (This is to deal with the fact that for some reason the app uses pandas and the names are in spanish)
    """
    if not d:
        return None
    k = {}

    for field_name, field_info in model.model_fields.items():
        column_name = model.__mapper__.attrs[field_name].columns[0].name
        typ = _unwrap_optional(field_info.annotation)
        if typ is str:
            k[field_name] = safe_parse_str(d.get(column_name, '')) 
            if k[field_name] == 'None':
                k[field_name] = safe_parse_str(d.get(field_name, '')) 
        elif typ is int:
            k[field_name] = safe_parse_int(d.get(column_name))
        elif typ is float:
            k[field_name] = safe_parse_float(d.get(column_name))
        elif typ is datetime:
            k[field_name] = safe_parse_date(d.get(column_name))
        else:
            k[field_name] = d.get(column_name, None)

    return model(**k)