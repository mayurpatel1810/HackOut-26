package ai.ecoforge.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.PositiveOrZero;
import java.time.Instant;
import java.util.UUID;

/**
 * Fields shared by every activity table. Quantity is validated as non-negative
 * here as well as in the database, because an invalid value must never reach a
 * calculation (Master Spec section 66).
 */
@MappedSuperclass
public abstract class ActivityRecordBase {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(name = "factory_id", nullable = false)
    private UUID factoryId;

    @PositiveOrZero(message = "A quantity cannot be negative. Emissions cannot be calculated from a negative activity value.")
    @Column(nullable = false)
    private Double quantity;

    @NotBlank(message = "A unit is required. EcoForge will not guess one.")
    @Column(nullable = false)
    private String unit;

    @Column(nullable = false)
    private String period = "YEAR";

    @Column(name = "data_quality", nullable = false)
    private String dataQuality = "ESTIMATED";

    @Column(nullable = false)
    private Double confidence = 0.65;

    @Column(nullable = false)
    private String provenance = "MANUAL";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public UUID getFactoryId() { return factoryId; }
    public void setFactoryId(UUID factoryId) { this.factoryId = factoryId; }
    public Double getQuantity() { return quantity; }
    public void setQuantity(Double quantity) { this.quantity = quantity; }
    public String getUnit() { return unit; }
    public void setUnit(String unit) { this.unit = unit; }
    public String getPeriod() { return period; }
    public void setPeriod(String period) { this.period = period; }
    public String getDataQuality() { return dataQuality; }
    public void setDataQuality(String dataQuality) { this.dataQuality = dataQuality; }
    public Double getConfidence() { return confidence; }
    public void setConfidence(Double confidence) { this.confidence = confidence; }
    public String getProvenance() { return provenance; }
    public void setProvenance(String provenance) { this.provenance = provenance; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }

    /** The label EcoForge shows and the key the engine resolves against. */
    public abstract String displayLabel();
    public abstract String engineKey();
    public abstract String recordType();
}
