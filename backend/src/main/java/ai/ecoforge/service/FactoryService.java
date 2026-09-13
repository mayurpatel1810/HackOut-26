package ai.ecoforge.service;

import ai.ecoforge.audit.AuditService;
import ai.ecoforge.dto.Dtos;
import ai.ecoforge.entity.*;
import ai.ecoforge.exception.NotFoundException;
import ai.ecoforge.repository.Repositories.*;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class FactoryService {

    private static final Map<String, Double> QUALITY_CONFIDENCE = Map.of(
            "MEASURED", 0.95, "INVOICED", 0.90, "ESTIMATED", 0.65, "ASSUMED", 0.40);

    private final FactoryRepository factories;
    private final FactoryProfileRepository profiles;
    private final EnergyRecordRepository energy;
    private final MaterialRecordRepository materials;
    private final WasteRecordRepository waste;
    private final ProcessRecordRepository processes;
    private final AuditService audit;

    public FactoryService(FactoryRepository factories, FactoryProfileRepository profiles,
                          EnergyRecordRepository energy, MaterialRecordRepository materials,
                          WasteRecordRepository waste, ProcessRecordRepository processes,
                          AuditService audit) {
        this.factories = factories;
        this.profiles = profiles;
        this.energy = energy;
        this.materials = materials;
        this.waste = waste;
        this.processes = processes;
        this.audit = audit;
    }

    public List<Dtos.FactoryResponse> list() {
        return factories.findAllByOrderByCreatedAtDesc().stream().map(this::toResponse).toList();
    }

    public Factory require(UUID id) {
        return factories.findById(id).orElseThrow(() -> new NotFoundException(
                "We could not find that factory. It may have been removed, or the link "
                + "may be out of date."));
    }

    public Dtos.FactoryResponse get(UUID id) { return toResponse(require(id)); }

    @Transactional
    public Dtos.FactoryResponse create(Dtos.FactoryRequest req, UUID ownerId) {
        Factory f = new Factory();
        apply(f, req);
        f.setOwnerId(ownerId);
        factories.save(f);

        FactoryProfile p = new FactoryProfile();
        p.setFactory(f);
        applyProfile(p, req);
        profiles.save(p);
        f.setProfile(p);

        audit.record(f.getId(), "FACTORY_CREATED", "factory", f.getId().toString(),
                Map.of("name", f.getName(), "industry", f.getIndustry(),
                       "country", f.getCountryCode()));
        return toResponse(f);
    }

    @Transactional
    public Dtos.FactoryResponse update(UUID id, Dtos.FactoryRequest req) {
        Factory f = require(id);
        apply(f, req);
        FactoryProfile p = f.getProfile();
        if (p == null) {
            p = new FactoryProfile();
            p.setFactory(f);
            f.setProfile(p);
        }
        applyProfile(p, req);
        profiles.save(p);
        factories.save(f);
        audit.record(id, "FACTORY_UPDATED", "factory", id.toString(), Map.of());
        return toResponse(f);
    }

    // --- activity data ------------------------------------------------------
    @Transactional
    public int replaceEnergy(UUID factoryId, List<Dtos.EnergyRequest> rows) {
        require(factoryId);
        energy.deleteByFactoryId(factoryId);
        rows.forEach(r -> {
            EnergyRecord e = new EnergyRecord();
            e.setFactoryId(factoryId);
            e.setEnergyType(r.energyType());
            e.setQuantity(r.quantity());
            e.setUnit(r.unit());
            e.setPeriod(orDefault(r.period(), "YEAR"));
            e.setSourceLabel(r.sourceLabel());
            e.setDataQuality(orDefault(r.dataQuality(), "ESTIMATED"));
            e.setProvenance(orDefault(r.provenance(), "MANUAL"));
            e.setConfidence(QUALITY_CONFIDENCE.getOrDefault(e.getDataQuality(), 0.65));
            energy.save(e);
        });
        audit.record(factoryId, "ENERGY_REPLACED", "energy_records", null,
                Map.of("count", rows.size()));
        return rows.size();
    }

    @Transactional
    public int replaceMaterials(UUID factoryId, List<Dtos.MaterialRequest> rows) {
        require(factoryId);
        materials.deleteByFactoryId(factoryId);
        rows.forEach(r -> {
            MaterialRecord m = new MaterialRecord();
            m.setFactoryId(factoryId);
            m.setMaterial(r.material());
            m.setMaterialGrade(r.materialGrade());
            m.setFunction(r.function());
            m.setQuantity(r.quantity());
            m.setUnit(r.unit());
            m.setPeriod(orDefault(r.period(), "YEAR"));
            m.setRecycledContentPct(r.recycledContentPct());
            m.setSupplier(r.supplier());
            m.setSupplierRegion(r.supplierRegion());
            m.setUnitCost(r.unitCost());
            m.setDataQuality(orDefault(r.dataQuality(), "ESTIMATED"));
            m.setProvenance(orDefault(r.provenance(), "MANUAL"));
            m.setConfidence(QUALITY_CONFIDENCE.getOrDefault(m.getDataQuality(), 0.6));
            materials.save(m);
        });
        audit.record(factoryId, "MATERIALS_REPLACED", "material_records", null,
                Map.of("count", rows.size()));
        return rows.size();
    }

    @Transactional
    public int replaceWaste(UUID factoryId, List<Dtos.WasteRequest> rows) {
        require(factoryId);
        waste.deleteByFactoryId(factoryId);
        rows.forEach(r -> {
            WasteRecord w = new WasteRecord();
            w.setFactoryId(factoryId);
            w.setWasteType(r.wasteType());
            w.setQuantity(r.quantity());
            w.setUnit(r.unit());
            w.setPeriod(orDefault(r.period(), "YEAR"));
            w.setTreatment(orDefault(r.treatment(), "LANDFILL"));
            w.setRecoveredPct(r.recoveredPct());
            w.setDisposalCost(r.disposalCost());
            w.setDataQuality(orDefault(r.dataQuality(), "ESTIMATED"));
            w.setProvenance(orDefault(r.provenance(), "MANUAL"));
            w.setConfidence(QUALITY_CONFIDENCE.getOrDefault(w.getDataQuality(), 0.7));
            waste.save(w);
        });
        audit.record(factoryId, "WASTE_REPLACED", "waste_records", null,
                Map.of("count", rows.size()));
        return rows.size();
    }

    @Transactional
    public int replaceProcesses(UUID factoryId, List<Dtos.ProcessRequest> rows) {
        require(factoryId);
        processes.deleteByFactoryId(factoryId);
        rows.forEach(r -> {
            ProcessRecord p = new ProcessRecord();
            p.setFactoryId(factoryId);
            p.setProcessName(r.processName());
            p.setProcessType(r.processType());
            p.setMachineType(r.machineType());
            p.setOperatingHours(r.operatingHours());
            p.setEnergySharePct(r.energySharePct());
            p.setMaterialInput(r.materialInput());
            p.setOutputQuantity(r.outputQuantity());
            p.setOutputUnit(r.outputUnit());
            p.setScrapRatePct(r.scrapRatePct());
            p.setOperatingTempC(r.operatingTempC());
            p.setDataQuality(orDefault(r.dataQuality(), "ESTIMATED"));
            processes.save(p);
        });
        audit.record(factoryId, "PROCESSES_REPLACED", "process_records", null,
                Map.of("count", rows.size()));
        return rows.size();
    }

    public List<EnergyRecord> energyOf(UUID id) { return energy.findByFactoryId(id); }
    public List<MaterialRecord> materialsOf(UUID id) { return materials.findByFactoryId(id); }
    public List<WasteRecord> wasteOf(UUID id) { return waste.findByFactoryId(id); }
    public List<ProcessRecord> processesOf(UUID id) { return processes.findByFactoryId(id); }

    // --- mapping ------------------------------------------------------------
    private void apply(Factory f, Dtos.FactoryRequest r) {
        f.setName(r.name());
        f.setIndustry(r.industry());
        f.setProductionType(r.productionType());
        f.setCountryCode(orDefault(r.countryCode(), "IN"));
        f.setStateOrRegion(r.stateOrRegion());
        f.setCity(r.city());
        f.setGridRegion(r.gridRegion());
    }

    private void applyProfile(FactoryProfile p, Dtos.FactoryRequest r) {
        p.setReportingYear(r.reportingYear() == null ? 2026 : r.reportingYear());
        p.setAnnualProduction(r.annualProduction());
        p.setProductionUnit(r.productionUnit());
        p.setEmployees(r.employees());
        p.setFloorAreaM2(r.floorAreaM2());
        p.setAnnualBudgetInr(r.annualBudgetInr());
        p.setTargetReductionPct(r.targetReductionPct());
        p.setCurrency(orDefault(r.currency(), "INR"));
        p.setElectricityTariffInrPerKwh(r.electricityTariffInrPerKwh());
        p.setDieselPriceInrPerLitre(r.dieselPriceInrPerLitre());
        p.setGasPriceInrPerM3(r.gasPriceInrPerM3());
        p.setLpgPriceInrPerKg(r.lpgPriceInrPerKg());
        p.setWasteDisposalCostInrPerTonne(r.wasteDisposalCostInrPerTonne());
    }

    private Dtos.FactoryResponse toResponse(Factory f) {
        FactoryProfile p = f.getProfile();
        return new Dtos.FactoryResponse(
                f.getId(), f.getName(), f.getIndustry(), f.getProductionType(),
                f.getCountryCode(), f.getStateOrRegion(), f.getCity(), f.getGridRegion(),
                f.isDemo(),
                p == null ? null : p.getReportingYear(),
                p == null ? null : p.getAnnualProduction(),
                p == null ? null : p.getProductionUnit(),
                p == null ? null : p.getEmployees(),
                p == null ? null : p.getFloorAreaM2(),
                p == null ? null : p.getAnnualBudgetInr(),
                p == null ? null : p.getTargetReductionPct(),
                p == null ? "INR" : p.getCurrency(),
                p == null ? null : p.getElectricityTariffInrPerKwh(),
                p == null ? null : p.getDieselPriceInrPerLitre(),
                p == null ? null : p.getGasPriceInrPerM3(),
                p == null ? null : p.getLpgPriceInrPerKg(),
                p == null ? null : p.getWasteDisposalCostInrPerTonne());
    }

    private static String orDefault(String v, String fallback) {
        return v == null || v.isBlank() ? fallback : v;
    }
}
