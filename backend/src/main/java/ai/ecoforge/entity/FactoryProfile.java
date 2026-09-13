package ai.ecoforge.entity;

import jakarta.persistence.*;
import java.util.UUID;

@Entity
@Table(name = "factory_profiles")
public class FactoryProfile {

    @Id
    @Column(name = "factory_id")
    private UUID factoryId;

    @OneToOne(fetch = FetchType.LAZY)
    @MapsId
    @JoinColumn(name = "factory_id")
    private Factory factory;

    @Column(name = "reporting_year", nullable = false)
    private Integer reportingYear = 2026;

    @Column(name = "reporting_period", nullable = false)
    private String reportingPeriod = "ANNUAL";

    @Column(name = "annual_production")
    private Double annualProduction;

    @Column(name = "production_unit")
    private String productionUnit;

    private Integer employees;

    @Column(name = "floor_area_m2")
    private Double floorAreaM2;

    @Column(name = "annual_budget_inr")
    private Double annualBudgetInr;

    @Column(nullable = false)
    private String currency = "INR";

    @Column(name = "target_reduction_pct")
    private Double targetReductionPct;

    @Column(name = "electricity_tariff_inr_per_kwh")
    private Double electricityTariffInrPerKwh;

    @Column(name = "diesel_price_inr_per_litre")
    private Double dieselPriceInrPerLitre;

    @Column(name = "gas_price_inr_per_m3")
    private Double gasPriceInrPerM3;

    @Column(name = "lpg_price_inr_per_kg")
    private Double lpgPriceInrPerKg;

    @Column(name = "waste_disposal_cost_inr_per_tonne")
    private Double wasteDisposalCostInrPerTonne;

    private String notes;

    public UUID getFactoryId() { return factoryId; }
    public void setFactoryId(UUID factoryId) { this.factoryId = factoryId; }
    public Factory getFactory() { return factory; }
    public void setFactory(Factory factory) { this.factory = factory; }
    public Integer getReportingYear() { return reportingYear; }
    public void setReportingYear(Integer reportingYear) { this.reportingYear = reportingYear; }
    public String getReportingPeriod() { return reportingPeriod; }
    public void setReportingPeriod(String reportingPeriod) { this.reportingPeriod = reportingPeriod; }
    public Double getAnnualProduction() { return annualProduction; }
    public void setAnnualProduction(Double annualProduction) { this.annualProduction = annualProduction; }
    public String getProductionUnit() { return productionUnit; }
    public void setProductionUnit(String productionUnit) { this.productionUnit = productionUnit; }
    public Integer getEmployees() { return employees; }
    public void setEmployees(Integer employees) { this.employees = employees; }
    public Double getFloorAreaM2() { return floorAreaM2; }
    public void setFloorAreaM2(Double floorAreaM2) { this.floorAreaM2 = floorAreaM2; }
    public Double getAnnualBudgetInr() { return annualBudgetInr; }
    public void setAnnualBudgetInr(Double annualBudgetInr) { this.annualBudgetInr = annualBudgetInr; }
    public String getCurrency() { return currency; }
    public void setCurrency(String currency) { this.currency = currency; }
    public Double getTargetReductionPct() { return targetReductionPct; }
    public void setTargetReductionPct(Double targetReductionPct) { this.targetReductionPct = targetReductionPct; }
    public Double getElectricityTariffInrPerKwh() { return electricityTariffInrPerKwh; }
    public void setElectricityTariffInrPerKwh(Double v) { this.electricityTariffInrPerKwh = v; }
    public Double getDieselPriceInrPerLitre() { return dieselPriceInrPerLitre; }
    public void setDieselPriceInrPerLitre(Double v) { this.dieselPriceInrPerLitre = v; }
    public Double getGasPriceInrPerM3() { return gasPriceInrPerM3; }
    public void setGasPriceInrPerM3(Double v) { this.gasPriceInrPerM3 = v; }
    public Double getLpgPriceInrPerKg() { return lpgPriceInrPerKg; }
    public void setLpgPriceInrPerKg(Double v) { this.lpgPriceInrPerKg = v; }
    public Double getWasteDisposalCostInrPerTonne() { return wasteDisposalCostInrPerTonne; }
    public void setWasteDisposalCostInrPerTonne(Double v) { this.wasteDisposalCostInrPerTonne = v; }
    public String getNotes() { return notes; }
    public void setNotes(String notes) { this.notes = notes; }
}
