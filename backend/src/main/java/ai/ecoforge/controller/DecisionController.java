package ai.ecoforge.controller;

import ai.ecoforge.dto.Dtos;
import ai.ecoforge.service.AnalysisOrchestrationService;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api")
public class DecisionController {

    private final AnalysisOrchestrationService orchestration;

    public DecisionController(AnalysisOrchestrationService orchestration) {
        this.orchestration = orchestration;
    }

    @PostMapping("/optimization/{factoryId}")
    public JsonNode optimise(@PathVariable UUID factoryId,
                             @Valid @RequestBody Dtos.OptimiseRequest req) {
        return orchestration.optimise(factoryId, req.budgetInr(), req.options());
    }

    @PostMapping("/optimization/{factoryId}/curve")
    public JsonNode curve(@PathVariable UUID factoryId,
                          @Valid @RequestBody Dtos.CurveRequest req) {
        return orchestration.curve(factoryId, req.budgets(), req.options());
    }

    @PostMapping("/simulations/{factoryId}")
    public JsonNode simulate(@PathVariable UUID factoryId,
                             @Valid @RequestBody Dtos.SimulateRequest req) {
        return orchestration.simulate(factoryId, req.selection(), req.options());
    }

    @PostMapping("/copilot/extract")
    public JsonNode extract(@Valid @RequestBody Dtos.ExtractRequest req) {
        return orchestration.extract(req.text());
    }

    @GetMapping("/evidence/sources")
    public JsonNode sources() { return orchestration.factorSources(); }

    @GetMapping("/public/ai-health")
    public JsonNode aiHealth() { return orchestration.aiHealth(); }
}
