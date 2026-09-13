package ai.ecoforge.exception;

public class ValidationException extends RuntimeException implements UserFacing {
    public ValidationException(String message) { super(message); }
    @Override public String userMessage() { return getMessage(); }
}
