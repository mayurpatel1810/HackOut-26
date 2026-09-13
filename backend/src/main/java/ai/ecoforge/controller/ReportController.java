package ai.ecoforge.controller;

import ai.ecoforge.dto.Dtos;
import ai.ecoforge.service.AnalysisOrchestrationService;
import ai.ecoforge.service.FactoryService;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.LocalDate;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.web.bind.annotation.*;

/**
 * Executive report (Master Spec section 59). Every section is assembled from
 * engine output only, and the report states which class each number belongs to,
 * so verified data is never silently mixed with scenario values.
 */
@RestController
@RequestMapping("/api/reports")
public class ReportController {

    private final AnalysisOrchestrationService orchestration;
    private final FactoryService factories;

    public ReportController(AnalysisOrchestrationService orchestration,
                            FactoryService factories) {
        this.orchestration = orchestration;
        this.factories = factories;
    }

    @PostMapping("/{factoryId}")
    public Map<String, Object> build(@PathVariable UUID factoryId,
                                     @RequestBody(required = false) Dtos.OptimiseRequest req) {
        double budget = (req == null || req.budgetInr() == null) ? 0d : req.budgetInr();
        Dtos.AnalyseOptions options = req == null ? null : req.options();

        JsonNode analysis = orchestration.analyse(factoryId, options);
        JsonNode plan = budget > 0
                ? orchestration.actionPlan(factoryId, budget, options)
                : null;

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("generated_on", LocalDate.now().toString());
        out.put("factory", factories.get(factoryId));
        out.put("executive_summary", Map.of(
                "total_t_co2e", analysis.path("total_t_co2e").asDouble(),
                "coverage_pct", analysis.path("coverage_pct").asDouble(),
                "data_confidence_pct", analysis.path("data_confidence_pct").asDouble(),
                "carbon_health", analysis.path("carbon_health").asDouble()));
        out.put("factory_footprint", analysis.path("by_node_t"));
        out.put("carbon_leak_points", analysis.path("hotspots"));
        out.put("circular_opportunities", analysis.path("recommendations"));
        out.put("decision_analysis", plan == null ? null : plan.path("portfolio"));
        out.put("recommended_portfolio",
                plan == null ? null : plan.path("portfolio").path("ledger"));
        out.put("action_plan", plan == null ? null : plan.path("plan"));
        out.put("evidence", analysis.path("calculations"));
        out.put("benchmark", analysis.path("benchmark"));
        out.put("data_classes", Map.of(
                "verified_data", "Emission factors from CEA v22.0, the EPA GHG Emission "
                        + "Factors Hub 2025 and the UK Government 2026 conversion factors.",
                "user_provided_data", "Activity quantities, units, periods, prices and "
                        + "budgets entered by the factory.",
                "curated_evidence", "Technical and cost evidence for circular "
                        + "interventions, curated by EcoForge with named sources. This is "
                        + "not an emission factor dataset.",
                "estimated_scenario", "What-If and portfolio values. Calculated from the "
                        + "above, but scenario values - not guaranteed outcomes."));
        out.put("assumptions", analysis.path("calculations"));
        out.put("limitations", Map.of(
                "coverage", analysis.path("coverage_detail"),
                "unresolved", analysis.path("unresolved"),
                "benchmark", analysis.path("benchmark")));
        return out;
    }
}
