# app/tool_security.py
import functools

class UnauthorizedToolAccessError(PermissionError):
    """Raised when an agent attempts to invoke a tool outside its permitted scope."""
    pass

def enforce_least_autonomy(allowed_agent_role: str):
    """
    Decorator enforcing the principle of least autonomy.
    Restricts execution of check_loan_application_status strictly to the 'LookupAgent'.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # In a multi-agent framework or execution context, we pass or check the active agent role.
            # Here we can inspect kwargs or thread/context state. Let's check agent_role in kwargs if provided.
            agent_role = kwargs.pop("agent_role", "UnknownAgent")
            
            if agent_role != allowed_agent_role:
                raise UnauthorizedToolAccessError(
                    f"Access Denied: Agent '{agent_role}' violated the principle of least autonomy. "
                    f"Only '{allowed_agent_role}' is authorized to invoke '{func.__name__}'."
                )
            
            print(f"[Security Policy] Least Autonomy Enforced: '{agent_role}' authorized for '{func.__name__}'.")
            return func(*args, **kwargs)
        return wrapper
    return decorator