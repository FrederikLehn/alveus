

# ======================================================================================================================
# Errors related to data input
# ======================================================================================================================
class LimitError(Exception):
    def __init__(self, message):
        super().__init__(message)


# ======================================================================================================================
# Errors related to typecurves
# ======================================================================================================================
class AssembleError(Exception):
    def __init__(self, message):
        super().__init__(message)


# ======================================================================================================================
# Errors related to optimization converge issues
# ======================================================================================================================
class ConvergenceError(Exception):
    def __init__(self, message):
        super().__init__(message)
