from typing import Any, Mapping, Sequence, Tuple


def bind_arguments(signature, args: Sequence[Any], kwargs: Mapping[str, Any]) -> Tuple[Sequence[Any], Mapping[str, Any]]:
    """
    Binds the given args and kwargs to the function's signature, applying defaults if necessary.
    """
    if signature:
        bound_args = signature.bind(*args, **kwargs)  # type: inspect.BoundArguments
        bound_args.apply_defaults()
        return bound_args.args, bound_args.kwargs
    else:
        return args, kwargs