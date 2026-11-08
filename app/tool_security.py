# app/tool_security.py
import functools

class UnauthorizedToolAccessError(PermissionError):
    """Raised when an agent attempts to invoke a tool outside its permitted scope."""
    pass

def enforce_least_autonomy(allowed_agent_role: str):
    """
    Enforces the principle of least autonomy.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # If agent_role is explicitly provided and doesn't match, block it.
            # If omitted, default to allowed_agent_role for backward compatibility with direct API entry points.
            agent_role = kwargs.pop("agent_role", allowed_agent_role)
            
            if agent_role != allowed_agent_role:
                raise UnauthorizedToolAccessError(
                    f"Access Denied: Agent '{agent_role}' violated the principle of least autonomy. "
                    f"Only '{allowed_agent_role}' is authorized to invoke '{func.__name__}'."
                )
            
            print(f"[Security Policy] Least Autonomy Enforced: '{agent_role}' authorized for '{func.__name__}' routine.")
            return func(*args, **kwargs)
        return wrapper
    return decorator