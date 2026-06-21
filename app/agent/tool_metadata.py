import inspect
import json
import signal
from typing import Any, Callable


def fn_metadata(fn: Callable[..., Any]) -> dict[str, Any]:
    sig = inspect.signature(fn)

    params = {}
    required = []

    for name, param in sig.parameters.items():
        annotation = (
            str(param.annotation)
            if param.annotation is not inspect.Parameter.empty
            else "Any"
        )

        params[name] = {
            "type": annotation,
            "default": (
                None
                if param.default is inspect.Parameter.empty
                else param.default
            ),
        }

        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "name": fn.__name__,
        "description": inspect.getdoc(fn) or "",
        "parameters": params,
        "required": required,
    }


def functions_metadata(functions: dict[str, Callable[..., Any]]) -> str:
    metadata = {
        fn_name: fn_metadata(fn)
        for fn_name, fn in functions.items()
    }
    return json.dumps(metadata, ensure_ascii=False, indent=2)


class TimeoutError(Exception):
    pass


def _timeout_handler(signum, frame):
    raise TimeoutError("Function timed out")


def wrap_function_with_timeout(fn, timeout_seconds: int = 5):
    def wrapped(**kwargs):
        return fn(**kwargs)
    return wrapped