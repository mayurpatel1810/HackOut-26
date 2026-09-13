package ai.ecoforge.exception;

import ai.ecoforge.dto.Dtos;
import jakarta.servlet.http.HttpServletRequest;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * Every error a user can see is written in plain language.
 * A stack trace or an exception class name never reaches the browser
 * (Master Spec section 64).
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Dtos.ApiError> onValidation(MethodArgumentNotValidException ex,
                                                      HttpServletRequest req) {
        Map<String, String> fields = new LinkedHashMap<>();
        ex.getBindingResult().getFieldErrors()
                .forEach(f -> fields.put(f.getField(), f.getDefaultMessage()));
        return ResponseEntity.badRequest().body(new Dtos.ApiError(
                "Some of the details need a small correction before we can continue.",
                null, requestId(req), fields));
    }

    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<Dtos.ApiError> onNotFound(NotFoundException ex,
                                                    HttpServletRequest req) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND).body(new Dtos.ApiError(
                ex.userMessage(), null, requestId(req), Map.of()));
    }

    @ExceptionHandler({ValidationException.class, IllegalArgumentException.class})
    public ResponseEntity<Dtos.ApiError> onBadRequest(RuntimeException ex,
                                                      HttpServletRequest req) {
        return ResponseEntity.badRequest().body(new Dtos.ApiError(
                ex.getMessage(), null, requestId(req), Map.of()));
    }

    @ExceptionHandler(AiServiceUnavailableException.class)
    public ResponseEntity<Dtos.ApiError> onAiDown(AiServiceUnavailableException ex,
                                                  HttpServletRequest req) {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(new Dtos.ApiError(
                ex.userMessage(), null, requestId(req), Map.of()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Dtos.ApiError> onAnything(Exception ex, HttpServletRequest req) {
        String id = requestId(req);
        log.error("unhandled error [{}]", id, ex);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(new Dtos.ApiError(
                "Something went wrong on our side. Nothing was saved. Please try again, "
                + "and quote reference " + id + " if it keeps happening.",
                null, id, Map.of()));
    }

    private String requestId(HttpServletRequest req) {
        Object id = req.getAttribute("requestId");
        return id != null ? id.toString() : UUID.randomUUID().toString().substring(0, 8);
    }
}
