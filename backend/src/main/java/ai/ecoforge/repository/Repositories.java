package ai.ecoforge.repository;

import ai.ecoforge.entity.*;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.jpa.repository.JpaRepository;

public final class Repositories {
    private Repositories() { }

    public interface FactoryRepository extends JpaRepository<Factory, UUID> {
        List<Factory> findAllByOrderByCreatedAtDesc();
        Optional<Factory> findFirstByDemoTrue();
    }

    public interface FactoryProfileRepository extends JpaRepository<FactoryProfile, UUID> { }

    public interface EnergyRecordRepository extends JpaRepository<EnergyRecord, UUID> {
        List<EnergyRecord> findByFactoryId(UUID factoryId);
        void deleteByFactoryId(UUID factoryId);
    }

    public interface MaterialRecordRepository extends JpaRepository<MaterialRecord, UUID> {
        List<MaterialRecord> findByFactoryId(UUID factoryId);
        void deleteByFactoryId(UUID factoryId);
    }

    public interface WasteRecordRepository extends JpaRepository<WasteRecord, UUID> {
        List<WasteRecord> findByFactoryId(UUID factoryId);
        void deleteByFactoryId(UUID factoryId);
    }

    public interface ProcessRecordRepository extends JpaRepository<ProcessRecord, UUID> {
        List<ProcessRecord> findByFactoryId(UUID factoryId);
        void deleteByFactoryId(UUID factoryId);
    }

    public interface UserRepository extends JpaRepository<AppUser, UUID> {
        Optional<AppUser> findByEmailIgnoreCase(String email);
    }

    public interface AuditLogRepository extends JpaRepository<AuditLog, Long> {
        List<AuditLog> findTop100ByFactoryIdOrderByCreatedAtDesc(UUID factoryId);
    }
}
