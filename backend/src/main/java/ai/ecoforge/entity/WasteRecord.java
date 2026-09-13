package ai.ecoforge.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "waste_records")
public class WasteRecord extends ActivityRecordBase {

    @Column(name = "waste_type", nullable = false)
    private String wasteType;

    @Column(nullable = false)
    private String treatment = "LANDFILL";

    @Column(name = "recovered_pct")
    private Double recoveredPct;

    @Column(name = "disposal_cost")
    private Double disposalCost;

    public String getWasteType() { return wasteType; }
    public void setWasteType(String wasteType) { this.wasteType = wasteType; }
    public String getTreatment() { return treatment; }
    public void setTreatment(String treatment) { this.treatment = treatment; }
    public Double getRecoveredPct() { return recoveredPct; }
    public void setRecoveredPct(Double recoveredPct) { this.recoveredPct = recoveredPct; }
    public Double getDisposalCost() { return disposalCost; }
    public void setDisposalCost(Double disposalCost) { this.disposalCost = disposalCost; }

    @Override public String displayLabel() { return wasteType; }
    @Override public String engineKey() {
        return wasteType == null ? "WASTE" : wasteType.toUpperCase().replaceAll("[^A-Z0-9]+", "_");
    }
    @Override public String recordType() { return "WASTE"; }
}
