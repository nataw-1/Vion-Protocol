"""
N VION Protocol — Exceptions
Every failure has a specific, named exception.
No more generic Python errors — every problem is identifiable.
"""


class NSoulError(Exception):
    """Base exception for all N VION Protocol errors."""
    def __init__(self, message: str, condition: int = 0):
        super().__init__(message)
        self.message = message
        self.condition = condition

    def __str__(self):
        if self.condition:
            return f"[N-VION Condition {self.condition}] {self.message}"
        return f"[N-VION] {self.message}"


# ─── CONSTITUTIONAL ERRORS ────────────────────────────────────────────────────

class ConstitutionError(NSoulError):
    """Base for all constitutional document errors."""
    pass

class ConstitutionNotFoundError(ConstitutionError):
    """VION.md or IDENTITY.md file not found at configured path."""
    pass

class ConstitutionIntegrityError(ConstitutionError):
    """Constitutional document has been modified since system start. Condition 6."""
    def __init__(self, message: str):
        super().__init__(message, condition=6)

class ConstitutionLoadError(ConstitutionError):
    """Failed to load or parse a constitutional document."""
    pass


# ─── AUTH ERRORS ──────────────────────────────────────────────────────────────

class AuthError(NSoulError):
    """Base for all authentication errors."""
    pass

class AuthTokenMissingError(AuthError):
    """No AUTH token provided with the command. Condition 1."""
    def __init__(self):
        super().__init__("No AUTH token provided. Command rejected.", condition=1)

class AuthTokenInvalidError(AuthError):
    """AUTH token provided but does not match. Condition 1."""
    def __init__(self):
        super().__init__("AUTH token is invalid. Command source not authorized.", condition=1)

class AuthTokenExpiredError(AuthError):
    """Command timestamp is outside the valid window."""
    def __init__(self, age_seconds: float, expiry_seconds: int):
        super().__init__(
            f"Command expired. Age: {int(age_seconds)}s, max allowed: {expiry_seconds}s.",
            condition=0
        )
        self.age_seconds = age_seconds
        self.expiry_seconds = expiry_seconds

class AuthNotConfiguredError(AuthError):
    """VION_AUTH_TOKEN environment variable not set."""
    def __init__(self):
        super().__init__(
            "VION_AUTH_TOKEN is not configured. Set it in your .env file before starting.",
            condition=0
        )


# ─── IDENTITY ERRORS ──────────────────────────────────────────────────────────

class IdentityError(NSoulError):
    """Base for all identity and registry errors."""
    pass

class AgentNotFoundError(IdentityError):
    """Agent ID not found in IDENTITY.md. Condition 1."""
    def __init__(self, agent_id: str):
        super().__init__(
            f"Agent '{agent_id}' is not registered in IDENTITY.md. No authority to act.",
            condition=1
        )
        self.agent_id = agent_id

class AgentSuspendedError(IdentityError):
    """Agent is registered but currently suspended. Condition 1."""
    def __init__(self, agent_id: str, agent_name: str):
        super().__init__(
            f"Agent '{agent_id}' ({agent_name}) is suspended. Owner review required.",
            condition=1
        )
        self.agent_id = agent_id
        self.agent_name = agent_name

class AgentTerminatedError(IdentityError):
    """Agent has been permanently terminated."""
    def __init__(self, agent_id: str, agent_name: str):
        super().__init__(
            f"Agent '{agent_id}' ({agent_name}) has been terminated and cannot be reactivated.",
            condition=1
        )
        self.agent_id = agent_id
        self.agent_name = agent_name

class ScopeViolationError(IdentityError):
    """Agent attempted an action outside its authorized scope. Condition 2."""
    def __init__(self, agent_id: str, action: str):
        super().__init__(
            f"Agent '{agent_id}' attempted out-of-scope action: '{action}'. "
            "Scope violation — Condition 2.",
            condition=2
        )
        self.agent_id = agent_id
        self.action = action

class IdentityRegistryError(IdentityError):
    """Failed to load or parse IDENTITY.md."""
    pass


# ─── COMMAND ERRORS ───────────────────────────────────────────────────────────

class CommandError(NSoulError):
    """Base for command processing errors."""
    pass

class InvalidCommandModeError(CommandError):
    """Unknown execution mode — must be DRY_RUN or LIVE."""
    def __init__(self, mode: str):
        super().__init__(f"Unknown execution mode: '{mode}'. Must be DRY_RUN or LIVE.")
        self.mode = mode

class SystemHaltedError(CommandError):
    """Command rejected because system is in HALT state."""
    def __init__(self):
        super().__init__(
            "System is HALTED. All commands are rejected until Owner issues a restart."
        )


# ─── HALT ENGINE ERRORS ───────────────────────────────────────────────────────

class HaltEngineError(NSoulError):
    """Base for HALT engine errors."""
    pass

class HaltConditionTriggeredError(HaltEngineError):
    """A HALT condition was triggered and full system shutdown occurred."""
    def __init__(self, condition: int, reason: str):
        super().__init__(
            f"HALT triggered — Condition {condition}: {reason}",
            condition=condition
        )
        self.reason = reason


# ─── CONFIGURATION ERRORS ─────────────────────────────────────────────────────

class ConfigError(NSoulError):
    """Base for configuration and environment errors."""
    pass

class ConfigMissingError(ConfigError):
    """Required environment variable or config value is missing."""
    def __init__(self, variable: str):
        super().__init__(
            f"Required configuration '{variable}' is missing. "
            f"Check your .env file and ensure '{variable}' is set."
        )
        self.variable = variable

class ConfigInvalidError(ConfigError):
    """Configuration value exists but is invalid."""
    def __init__(self, variable: str, reason: str):
        super().__init__(f"Configuration '{variable}' is invalid: {reason}")
        self.variable = variable


# ─── LOG ERRORS ───────────────────────────────────────────────────────────────

class LogError(NSoulError):
    """Base for logging errors."""
    pass

class LogIntegrityError(LogError):
    """Log chain integrity check failed — log may have been tampered with. Condition 6."""
    def __init__(self, entry_index: int):
        super().__init__(
            f"Log integrity chain broken at entry {entry_index}. "
            "Log may have been tampered with. Constitutional integrity violation — Condition 6.",
            condition=6
        )
        self.entry_index = entry_index
