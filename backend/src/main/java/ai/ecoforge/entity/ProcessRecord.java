package ai.ecoforge.entity;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "process_records")
public class ProcessRecord {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(name = "factory_id", nullable = false)
    private UUID factoryId;

    @Column(name = "process_name", nullable = false)
    private String processName;

    @Column(name = "process_type")
    private String processType;

    @Column(name = "machine_type")
    private String machineType;

    @Column(name = "operating_hours")
    private Double operatingHours;

    @Column(name = "energy_share_pct")
    private Double energySharePct;

    @Column(name = "material_input")
    private String materialInput;

    @Column(name = "output_quantity")
    private Double outputQuantity;

    @Column(name = "output_unit")
    private String outputUnit;

    @Column(name = "scrap_rate_pct")
    private Double scrapRatePct;

    @Column(name = "operating_temp_c")
    private Double operatingTempC;

    @Column(name = "data_quality", nullable = false)
    private String dataQuality = "ESTIMATED";

    @Column(nullable = false)
    private Double confidence = 0.6;

    @Column(nullable = false)
    private String provenance = "MANUAL";

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public UUID getFactoryId() { return factoryId; }
    public void setFactoryId(UUID factoryId) { this.factoryId = factoryId; }
    public String getProcessName() { return processName; }
    public void setProcessName(String processName) { this.processName = processName; }
    public String getProcessType() { return processType; }
    public void setProcessType(String processType) { this.processType = processType; }
    public String getMachineType() { return machineType; }
    public void setMachineType(String machineType) { this.machineType = machineType; }
    public Double getOperatingHours() { return operatingHours; }
    public void setOperatingHours(Double operatingHours) { this.operatingHours = operatingHours; }
    public Double getEnergySharePct() { return energySharePct; }
    public void setEnergySharePct(Double energySharePct) { this.energySharePct = energySharePct; }
    public String getMaterialInput() { return materialInput; }
    public void setMaterialInput(String materialInput) { this.materialInput = materialInput; }
    public Double getOutputQuantity() { return outputQuantity; }
    public void setOutputQuantity(Double outputQuantity) { this.outputQuantity = outputQuantity; }
    public String getOutputUnit() { return outputUnit; }
    public void setOutputUnit(String outputUnit) { this.outputUnit = outputUnit; }
    public Double getScrapRatePct() { return scrapRatePct; }
    public void setScrapRatePct(Double scrapRatePct) { this.scrapRatePct = scrapRatePct; }
    public Double getOperatingTempC() { return operatingTempC; }
    public void setOperatingTempC(Double operatingTempC) { this.operatingTempC = operatingTempC; }
    public String getDataQuality() { return dataQuality; }
    public void setDataQuality(String dataQuality) { this.dataQuality = dataQuality; }
    public Double getConfidence() { return confidence; }
    public void setConfidence(Double confidence) { this.confidence = confidence; }
    public String getProvenance() { return provenance; }
    public void setProvenance(String provenance) { this.provenance = provenance; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
}
