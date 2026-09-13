package ai.ecoforge.service;

import ai.ecoforge.audit.AuditService;
import ai.ecoforge.dto.Dtos;
import ai.ecoforge.entity.*;
import com.fasterxml.jackson.databind.JsonNode;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;

/**
 * Turns stored factory data into the payload the deterministic engine expects,
 * calls it, and records what was asked for.
 *
 * Spring Boot deliberately performs NO carbon arithmetic. There is exactly one
 * implementation of the emission engine, it lives in the Python service, and it
 * is the one covered by the test suite.
 */
@Service
public class AnalysisOrchestrationService {

    private final FactoryService factories;
    private final AiServiceClient ai;
    private final AuditService audit;

    public AnalysisOrchestrationService(FactoryService factories, AiServiceClient ai,
                                        AuditService audit) {
        this.factories = factories;
        this.ai = ai;
        this.audit = audit;
    }

    // --- payload assembly ---------------------------------------------------
    public Map<String, Object> payload(UUID factoryId, Dtos.AnalyseOptions options) {
        Factory f = factories.require(factoryId);
        FactoryProfile p = f.getProfile();

        Map<String, Object> factory = new LinkedHashMap<>();
        factory.put("factory_id", f.getId().toString());
        factory.put("name", f.getName());
        factory.put("industry", f.getIndustry());
        factory.put("country_code", f.getCountryCode());
        factory.put("state_or_region", f.getStateOrRegion());
        factory.put("grid_region", f.getGridRegion());
        factory.put("reporting_year", p == null || p.getReportingYear() == null
                ? 2026 : p.getReportingYear());
        factory.put("annual_production", p == null ? null : p.getAnnualProduction());
        factory.put("production_unit", p == null ? null : p.getProductionUnit());
        factory.put("employees", p == null ? null : p.getEmployees());
        factory.put("budget_inr", budget(p, options));
        factory.put("target_reduction_pct", p == null ? null : p.getTargetReductionPct());
        factory.put("roof_area_m2", p == null ? null : p.getFloorAreaM2());
        factory.put("currency", p == null ? "INR" : p.getCurrency());
        // Prices drive savings and payback. They are passed through exactly as
        // entered; the engine refuses to assume one when it is absent.
        factory.put("electricity_tariff_inr_per_kwh",
                p == null ? null : p.getElectricityTariffInrPerKwh());
        factory.put("diesel_price_inr_per_litre",
                p == null ? null : p.getDieselPriceInrPerLitre());
        factory.put("gas_price_inr_per_m3", p == null ? null : p.getGasPriceInrPerM3());
        factory.put("lpg_price_inr_per_kg", p == null ? null : p.getLpgPriceInrPerKg());
        factory.put("waste_disposal_cost_inr_per_tonne",
                p == null ? null : p.getWasteDisposalCostInrPerTonne());

        List<Map<String, Object>> records = new ArrayList<>();
        for (EnergyRecord e : factories.energyOf(factoryId)) {
            records.add(base(e, "ENERGY", e.displayLabel(), e.engineKey()));
        }
        for (MaterialRecord m : factories.materialsOf(factoryId)) {
            Map<String, Object> row = base(m, "MATERIAL", m.displayLabel(), m.engineKey());
            row.put("material", m.getMaterial());
            row.put("material_grade", m.getMaterialGrade());
            row.put("function", m.getFunction());
            row.put("recycled_content_pct", m.getRecycledContentPct());
            row.put("supplier_region", m.getSupplierRegion());
            row.put("unit_cost", m.getUnitCost());
            records.add(row);
        }
        for (WasteRecord w : factories.wasteOf(factoryId)) {
            Map<String, Object> row = base(w, "WASTE", w.displayLabel(), w.engineKey());
            row.put("material", w.getWasteType());
            row.put("treatment", w.getTreatment());
            records.add(row);
        }

        List<Map<String, Object>> processes = new ArrayList<>();
        for (ProcessRecord pr : factories.processesOf(factoryId)) {
            Map<String, Object> row = new LinkedHashMap<>();
            row.put("process_name", pr.getProcessName());
            row.put("process_type", pr.getProcessType());
            row.put("machine_type", pr.getMachineType());
            row.put("operating_hours", pr.getOperatingHours());
            row.put("energy_share_pct", pr.getEnergySharePct());
            row.put("output_quantity", pr.getOutputQuantity());
            row.put("output_unit", pr.getOutputUnit());
            row.put("scrap_rate_pct", pr.getScrapRatePct());
            row.put("operating_temp_c", pr.getOperatingTempC());
            processes.add(row);
        }

        Map<String, Object> constraints = new LinkedHashMap<>();
        constraints.put("budget_inr", budget(p, options));
        constraints.put("max_payback_years",
                options == null ? null : options.maxPaybackYears());
        constraints.put("min_confidence",
                options == null || options.minConfidence() == null ? "low" : options.minConfidence());
        constraints.put("strictness",
                options == null || options.strictness() == null ? "BALANCED" : options.strictness());
        constraints.put("weights", options == null ? null : options.weights());

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("factory", factory);
        body.put("records", records);
        body.put("view", options == null || options.view() == null
                ? "operational" : options.view());
        body.put("constraints", constraints);
        body.put("history", options == null || options.history() == null
                ? List.of() : options.history());
        body.put("processes", processes);
        return body;
    }

    private Double budget(FactoryProfile p, Dtos.AnalyseOptions options) {
        if (options != null && options.budgetInr() != null) {
            return options.budgetInr();
        }
        return p == null ? null : p.getAnnualBudgetInr();
    }

    private Map<String, Object> base(ActivityRecordBase r, String type, String label,
                                     String key) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("record_id", r.getId() == null ? UUID.randomUUID().toString()
                                               : r.getId().toString());
        row.put("record_type", type);
        row.put("label", label);
        row.put("key", key);
        row.put("quantity", r.getQuantity());
        row.put("unit", r.getUnit());
        row.put("period", r.getPeriod());
        row.put("data_quality", r.getDataQuality());
        row.put("provenance", r.getProvenance());
        return row;
    }

    // --- calls --------------------------------------------------------------
    public JsonNode analyse(UUID factoryId, Dtos.AnalyseOptions options) {
        JsonNode out = ai.post("/ai/analyse", payload(factoryId, options));
        audit.record(factoryId, "ANALYSIS_RUN", "analysis", null, Map.of(
                "total_t_co2e", out.path("total_t_co2e").asDouble(),
                "coverage_pct", out.path("coverage_pct").asDouble(),
                "view", out.path("view").asText()));
        return out;
    }

    public JsonNode optimise(UUID factoryId, double budget, Dtos.AnalyseOptions options) {
        Map<String, Object> body = payload(factoryId, options);
        body.put("budget_inr", budget);
        JsonNode out = ai.post("/ai/optimize", body);
        audit.record(factoryId, "OPTIMISATION_RUN", "optimization_runs", null, Map.of(
                "budget_inr", budget,
                "reduction_t", out.path("total_reduction_t").asDouble(),
                "actions", out.path("action_count").asInt()));
        return out;
    }

    public JsonNode curve(UUID factoryId, List<Double> budgets, Dtos.AnalyseOptions options) {
        Map<String, Object> body = payload(factoryId, options);
        body.put("budgets", budgets);
        return ai.post("/ai/optimize/curve", body);
    }

    public JsonNode simulate(UUID factoryId, List<String> selection,
                             Dtos.AnalyseOptions options) {
        Map<String, Object> body = payload(factoryId, options);
        body.put("selection", selection);
        JsonNode out = ai.post("/ai/simulate", body);
        audit.record(factoryId, "SIMULATION_RUN", "simulation_scenarios", null, Map.of(
                "selection", selection,
                "reduction_pct", out.path("reduction_pct").asDouble()));
        return out;
    }

    public JsonNode actionPlan(UUID factoryId, double budget, Dtos.AnalyseOptions options) {
        Map<String, Object> body = payload(factoryId, options);
        body.put("budget_inr", budget);
        JsonNode out = ai.post("/ai/action-plan", body);
        audit.record(factoryId, "ACTION_PLAN_GENERATED", "action_plans", null,
                Map.of("budget_inr", budget));
        return out;
    }

    public JsonNode evidence(UUID factoryId, Dtos.CopilotRequest req) {
        Map<String, Object> body = payload(factoryId, req.options());
        body.put("question", req.question());
        body.put("selection", req.selection() == null ? List.of() : req.selection());
        body.put("budget_inr", req.budgetInr());
        return ai.post("/ai/evidence", body);
    }

    public JsonNode copilot(UUID factoryId, Dtos.CopilotRequest req) {
        Map<String, Object> body = payload(factoryId, req.options());
        body.put("question", req.question());
        body.put("selection", req.selection() == null ? List.of() : req.selection());
        body.put("budget_inr", req.budgetInr());
        JsonNode out = ai.post("/ai/copilot", body);
        audit.record(factoryId, "COPILOT_QUERY", "copilot_conversations", null, Map.of(
                "question", req.question(),
                "mode", out.path("meta").path("mode").asText()));
        return out;
    }

    public JsonNode anomaly(UUID factoryId, Dtos.AnalyseOptions options) {
        return ai.post("/ai/anomaly", payload(factoryId, options));
    }

    public JsonNode extract(String text) {
        return ai.post("/ai/extract", Map.of("text", text));
    }

    public JsonNode factorSources() { return ai.get("/factors/sources"); }

    public JsonNode aiHealth() { return ai.get("/health"); }
}
