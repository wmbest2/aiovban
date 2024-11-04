import functools
import logging
from dataclasses import Field, field

SYNTHETIC_NAME = "synthetic_name"

MASK = "mask"

logger = logging.getLogger(__package__)


def named_synthetic(name, mask=0xFF, offset=0, **kwargs) -> Field:
    return field(
        metadata={f"{SYNTHETIC_NAME}": name, "mask": mask, "offset": offset}, **kwargs
    )


def subprotocol(value) -> Field:
    return named_synthetic("subprotocol", mask=0xE0, default=value)


def subprotocol_data() -> Field:
    return named_synthetic("subprotocol_data", mask=0x1F, default=0)


def byte_a(mask=0xFF, **kwargs) -> Field:
    return named_synthetic("byte_a", mask, **kwargs)


def byte_b(mask=0xFF, **kwargs) -> Field:
    return named_synthetic("byte_b", mask, **kwargs)


def byte_c(mask=0xFF, **kwargs) -> Field:
    return named_synthetic("byte_c", mask, **kwargs)


class SyntheticMixin:
    """
    This class is a mixin that will create synthetic properties
    for each field that has the same synthetic_name metadata.
    """

    def __post_init__(self):
        from itertools import groupby

        masks_by_name = {
            k: list(v)
            for k, v in groupby(
                self.__dataclass_fields__.values(),
                key=lambda x: x.metadata.get(SYNTHETIC_NAME),
            )
        }
        masks_by_name.__delitem__(None)

        for synthetic, fields in masks_by_name.items():
            assert sum(f.metadata[MASK] for f in fields) <= 0xFF

            def getter(s, fields=fields):
                return functools.reduce(
                    lambda x, y: x
                    | (int(getattr(s, y.name)) & y.metadata[MASK])
                    - y.metadata["offset"],
                    fields,
                    0,
                )

            def setter(s, value, fields=fields):
                if value is None:
                    return
                for f in fields:
                    try:
                        setattr(
                            s,
                            f.name,
                            f.type(
                                (int(value) & f.metadata[MASK]) + f.metadata["offset"]
                            ),
                        )
                    except TypeError as e:
                        logger.error(f"Error with field {f.name} for value {value}", e)

            def deleter(s, fields=fields):
                for f in fields:
                    delattr(s, f.name)

            setattr(
                self.__class__,
                synthetic,
                property(fget=getter, fset=setter, fdel=deleter),
            )
