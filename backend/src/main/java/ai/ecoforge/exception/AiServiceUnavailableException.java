package ai.ecoforge.exception;

public class AiServiceUnavailableException extends RuntimeException implements UserFacing {
    public AiServiceUnavailableException(String message) { super(message); }
    @Override public String userMessage() { return getMessage(); }
}
