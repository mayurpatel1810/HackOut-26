package ai.ecoforge.exception;

public class NotFoundException extends RuntimeException implements UserFacing {
    public NotFoundException(String message) { super(message); }
    @Override public String userMessage() { return getMessage(); }
}
