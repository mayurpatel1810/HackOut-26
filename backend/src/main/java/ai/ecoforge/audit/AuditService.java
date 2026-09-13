package ai.ecoforge.audit;

import ai.ecoforge.entity.AuditLog;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Service;

/**
 * Audit trail for anything that changes data or produces a number a user might
 * later be asked to defend (Master Spec section 63). Secrets are never logged.
 *
 * Deliberately NOT transactional: the write happens in {@link AuditWriter}, one
 * proxy hop away, so a failure there can be caught here without poisoning the
 * caller's transaction.
 */
@Service
public class AuditService {

    private static final Logger log = LoggerFactory.getLogger(AuditService.class);
    private static final java.util.Set<String> REDACT =
            java.util.Set.of("password", "token", "secret", "apikey", "api_key",
                    "authorization", "jwt");

    private final AuditWriter writer;
    private final ObjectMapper mapper;

    public AuditService(AuditWriter writer, ObjectMapper mapper) {
        this.writer = writer;
        this.mapper = mapper;
    }

    public void record(UUID factoryId, String action, String entity, String entityId,
                       Map<String, Object> detail) {
        try {
            AuditLog row = new AuditLog();
            row.setActor(currentActor());
            row.setFactoryId(factoryId);
            row.setAction(action);
            row.setEntity(entity);
            row.setEntityId(entityId);
            row.setDetail(mapper.writeValueAsString(redact(detail)));
            writer.write(row);
        } catch (Exception ex) {
            // An audit failure must never break the user's request.
            log.warn("audit write failed for action {}: {}", action, ex.toString());
        }
    }

    private Map<String, Object> redact(Map<String, Object> detail) {
        if (detail == null) {
            return Map.of();
        }
        var copy = new java.util.LinkedHashMap<String, Object>();
        detail.forEach((k, v) -> copy.put(k,
                REDACT.contains(k.toLowerCase().replace("-", "")) ? "[redacted]" : v));
        return copy;
    }

    private String currentActor() {
        var auth = SecurityContextHolder.getContext().getAuthentication();
        return auth == null ? "anonymous" : auth.getName();
    }
}