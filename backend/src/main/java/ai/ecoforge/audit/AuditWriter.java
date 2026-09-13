package ai.ecoforge.audit;

import ai.ecoforge.entity.AuditLog;
import ai.ecoforge.repository.Repositories.AuditLogRepository;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

@Component
public class AuditWriter {

    private final AuditLogRepository repo;

    public AuditWriter(AuditLogRepository repo) {
        this.repo = repo;
    }

    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void write(AuditLog row) {
        repo.saveAndFlush(row);
    }
}