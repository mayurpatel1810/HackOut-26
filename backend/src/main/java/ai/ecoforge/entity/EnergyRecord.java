package ai.ecoforge.entity;

import jakarta.persistence.*;
import java.time.LocalDate;

@Entity
@Table(name = "energy_records")
public class EnergyRecord extends ActivityRecordBase {

    @Column(name = "energy_type", nullable = false)
    private String energyType;

    @Column(name = "period_start")
    private LocalDate periodStart;

    @Column(name = "period_end")
    private LocalDate periodEnd;

    @Column(name = "source_label")
    private String sourceLabel;

    public String getEnergyType() { return energyType; }
    public void setEnergyType(String energyType) { this.energyType = energyType; }
    public LocalDate getPeriodStart() { return periodStart; }
    public void setPeriodStart(LocalDate periodStart) { this.periodStart = periodStart; }
    public LocalDate getPeriodEnd() { return periodEnd; }
    public void setPeriodEnd(LocalDate periodEnd) { this.periodEnd = periodEnd; }
    public String getSourceLabel() { return sourceLabel; }
    public void setSourceLabel(String sourceLabel) { this.sourceLabel = sourceLabel; }

    @Override public String displayLabel() {
        return sourceLabel != null && !sourceLabel.isBlank() ? sourceLabel : energyType;
    }
    @Override public String engineKey() { return energyType; }
    @Override public String recordType() { return "ENERGY"; }
}
