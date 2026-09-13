package ai.ecoforge.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "material_records")
public class MaterialRecord extends ActivityRecordBase {

    @Column(nullable = false)
    private String material;

    @Column(name = "material_grade")
    private String materialGrade;

    /** What the material DOES in the process - drives function-aware retrieval. */
    @Column(name = "function")
    private String function;

    @Column(name = "recycled_content_pct")
    private Double recycledContentPct;

    private String supplier;

    @Column(name = "supplier_region")
    private String supplierRegion;

    @Column(name = "unit_cost")
    private Double unitCost;

    public String getMaterial() { return material; }
    public void setMaterial(String material) { this.material = material; }
    public String getMaterialGrade() { return materialGrade; }
    public void setMaterialGrade(String materialGrade) { this.materialGrade = materialGrade; }
    public String getFunction() { return function; }
    public void setFunction(String function) { this.function = function; }
    public Double getRecycledContentPct() { return recycledContentPct; }
    public void setRecycledContentPct(Double recycledContentPct) { this.recycledContentPct = recycledContentPct; }
    public String getSupplier() { return supplier; }
    public void setSupplier(String supplier) { this.supplier = supplier; }
    public String getSupplierRegion() { return supplierRegion; }
    public void setSupplierRegion(String supplierRegion) { this.supplierRegion = supplierRegion; }
    public Double getUnitCost() { return unitCost; }
    public void setUnitCost(Double unitCost) { this.unitCost = unitCost; }

    @Override public String displayLabel() { return material; }
    @Override public String engineKey() {
        return material == null ? "MATERIAL" : material.toUpperCase().replaceAll("[^A-Z0-9]+", "_");
    }
    @Override public String recordType() { return "MATERIAL"; }
}
