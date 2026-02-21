"""
Central tool registry. Each tool module registers itself via the @tool decorator.
brain.py imports TOOLS + DISPATCH from here via agent/tools/__init__.py.
"""

_registry: list[dict] = []


def tool(spec: dict):
    """Decorator that registers a handler function with its Anthropic tool spec."""
    def decorator(fn):
        _registry.append({"spec": spec, "fn": fn})
        return fn
    return decorator


def get_tools() -> list[dict]:
    """Return all registered tool specs (Anthropic format)."""
    return [e["spec"] for e in _registry]


def get_dispatch() -> dict:
    """Return a name→handler mapping for all registered tools."""
    return {e["spec"]["name"]: e["fn"] for e in _registry}
