package ai.ecoforge.exception;

/** Marker for exceptions whose message is safe to show a factory manager. */
public interface UserFacing {
    String userMessage();
}
