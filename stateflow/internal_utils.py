from typing import Any, Mapping, Sequence, Tuple
import inspect
from inspect import Signature, BoundArguments


def bind_arguments(
    signature: Signature | None,
    args: Sequence[Any],
    kwargs: Mapping[str, Any]
) -> Tuple[tuple[Any, ...], Mapping[str, Any]]:
    """
    Binds the given args and kwargs to the function's signature, applying defaults if necessary.
    """
    if signature:
        bound_args: BoundArguments = signature.bind(*args, **kwargs)
        bound_args.apply_defaults()
        return bound_args.args, bound_args.kwargs
    else:
        return tuple(args), kwargs
