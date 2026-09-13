package ai.ecoforge.controller;

import ai.ecoforge.dto.Dtos;
import ai.ecoforge.service.FactoryService;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/factories")
public class FactoryController {

    private final FactoryService factories;

    public FactoryController(FactoryService factories) { this.factories = factories; }

    @GetMapping
    public List<Dtos.FactoryResponse> list() { return factories.list(); }

    @GetMapping("/{id}")
    public Dtos.FactoryResponse get(@PathVariable UUID id) { return factories.get(id); }

    @PostMapping
    public Dtos.FactoryResponse create(@Valid @RequestBody Dtos.FactoryRequest req) {
        return factories.create(req, null);
    }

    @PutMapping("/{id}")
    public Dtos.FactoryResponse update(@PathVariable UUID id,
                                       @Valid @RequestBody Dtos.FactoryRequest req) {
        return factories.update(id, req);
    }

    @PutMapping("/{id}/energy")
    public Map<String, Object> energy(@PathVariable UUID id,
                                      @Valid @RequestBody List<Dtos.EnergyRequest> rows) {
        return Map.of("saved", factories.replaceEnergy(id, rows));
    }

    @PutMapping("/{id}/materials")
    public Map<String, Object> materials(@PathVariable UUID id,
                                         @Valid @RequestBody List<Dtos.MaterialRequest> rows) {
        return Map.of("saved", factories.replaceMaterials(id, rows));
    }

    @PutMapping("/{id}/waste")
    public Map<String, Object> waste(@PathVariable UUID id,
                                     @Valid @RequestBody List<Dtos.WasteRequest> rows) {
        return Map.of("saved", factories.replaceWaste(id, rows));
    }

    @PutMapping("/{id}/processes")
    public Map<String, Object> processes(@PathVariable UUID id,
                                         @Valid @RequestBody List<Dtos.ProcessRequest> rows) {
        return Map.of("saved", factories.replaceProcesses(id, rows));
    }

    @PutMapping("/{id}/activity")
    public Map<String, Object> bulk(@PathVariable UUID id,
                                    @Valid @RequestBody Dtos.BulkActivityRequest req) {
        int e = req.energy() == null ? 0 : factories.replaceEnergy(id, req.energy());
        int m = req.materials() == null ? 0 : factories.replaceMaterials(id, req.materials());
        int w = req.waste() == null ? 0 : factories.replaceWaste(id, req.waste());
        int p = req.processes() == null ? 0 : factories.replaceProcesses(id, req.processes());
        return Map.of("energy", e, "materials", m, "waste", w, "processes", p);
    }

    @GetMapping("/{id}/activity")
    public Map<String, Object> activity(@PathVariable UUID id) {
        return Map.of(
                "energy", factories.energyOf(id),
                "materials", factories.materialsOf(id),
                "waste", factories.wasteOf(id),
                "processes", factories.processesOf(id));
    }
}
