package ai.ecoforge.controller;

import ai.ecoforge.dto.Dtos;
import ai.ecoforge.service.AnalysisOrchestrationService;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.Valid;
import java.util.UUID;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/factories/{id}")
public class AnalysisController {

    private final AnalysisOrchestrationService orchestration;

    public AnalysisController(AnalysisOrchestrationService orchestration) {
        this.orchestration = orchestration;
    }

    private static Dtos.AnalyseOptions viewOnly(String view) {
        return new Dtos.AnalyseOptions(view, null, null, null, null, null, null);
    }

    @PostMapping("/analyze")
    public JsonNode analyze(@PathVariable UUID id,
                            @RequestBody(required = false) Dtos.AnalyseOptions options) {
        return orchestration.analyse(id, options);
    }

    @GetMapping("/footprint")
    public JsonNode footprint(@PathVariable UUID id,
                              @RequestParam(defaultValue = "operational") String view) {
        return orchestration.analyse(id, viewOnly(view));
    }

    @GetMapping("/hotspots")
    public JsonNode hotspots(@PathVariable UUID id,
                             @RequestParam(defaultValue = "operational") String view) {
        return orchestration.analyse(id, viewOnly(view)).path("hotspots");
    }

    @GetMapping("/recommendations")
    public JsonNode recommendations(@PathVariable UUID id,
                                    @RequestParam(defaultValue = "operational") String view) {
        return orchestration.analyse(id, viewOnly(view)).path("recommendations");
    }

    @GetMapping("/twin")
    public JsonNode twin(@PathVariable UUID id,
                         @RequestParam(defaultValue = "operational") String view) {
        return orchestration.analyse(id, viewOnly(view)).path("twin");
    }

    @GetMapping("/anomalies")
    public JsonNode anomalies(@PathVariable UUID id) {
        return orchestration.anomaly(id, null);
    }

    @PostMapping("/action-plan")
    public JsonNode actionPlan(@PathVariable UUID id,
                               @Valid @RequestBody Dtos.OptimiseRequest req) {
        return orchestration.actionPlan(id, req.budgetInr(), req.options());
    }

    @PostMapping("/copilot")
    public JsonNode copilot(@PathVariable UUID id,
                            @Valid @RequestBody Dtos.CopilotRequest req) {
        return orchestration.copilot(id, req);
    }

    @PostMapping("/evidence")
    public JsonNode evidence(@PathVariable UUID id,
                             @Valid @RequestBody Dtos.CopilotRequest req) {
        return orchestration.evidence(id, req);
    }
}
