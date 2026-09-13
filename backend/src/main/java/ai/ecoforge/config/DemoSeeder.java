package ai.ecoforge.config;

import ai.ecoforge.dto.Dtos;
import ai.ecoforge.entity.Factory;
import ai.ecoforge.repository.Repositories.FactoryRepository;
import ai.ecoforge.service.FactoryService;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.ApplicationArguments;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Seeds the demo factory (Master Spec section 60).
 *
 * Only OPERATIONAL INPUTS are seeded. No emission, leak, recommendation, cost or
 * scenario value is ever written here - all of those are calculated at request
 * time from the verified factor table, so the demo cannot drift away from the
 * engine.
 */
@Configuration
public class DemoSeeder {

    private static final Logger log = LoggerFactory.getLogger(DemoSeeder.class);
    private static final String[] CANDIDATE_PATHS = {
            "data/curated/demo_factory.json",
            "../data/curated/demo_factory.json",
            "/srv/data/curated/demo_factory.json"
    };

    @Bean
    public ApplicationRunner seedDemoFactory(EcoForgeProperties props,
                                             FactoryRepository factories,
                                             FactoryService service,
                                             ObjectMapper mapper) {
        return (ApplicationArguments args) -> {
            if (!props.getDemo().isSeedOnStartup()) {
                return;
            }
            if (factories.findFirstByDemoTrue().isPresent()) {
                log.info("demo factory already present; not reseeding");
                return;
            }
            JsonNode root = read(mapper);
            if (root == null) {
                log.warn("demo_factory.json not found on any known path; skipping seed. "
                        + "Set SEED_DEMO=false to silence this.");
                return;
            }
            JsonNode f = root.path("factory");
            Dtos.FactoryRequest req = new Dtos.FactoryRequest(
                    f.path("name").asText(),
                    f.path("industry").asText(),
                    f.path("production_type").asText(null),
                    f.path("country_code").asText("IN"),
                    f.path("state_or_region").asText(null),
                    f.path("city").asText(null),
                    f.path("grid_region").asText(null),
                    f.path("reporting_year").asInt(2026),
                    f.path("annual_production").isMissingNode() ? null
                            : f.path("annual_production").asDouble(),
                    f.path("production_unit").asText(null),
                    f.path("employees").isMissingNode() ? null : f.path("employees").asInt(),
                    f.path("roof_area_m2").isMissingNode() ? null
                            : f.path("roof_area_m2").asDouble(),
                    f.path("budget_inr").isMissingNode() ? null : f.path("budget_inr").asDouble(),
                    f.path("target_reduction_pct").isMissingNode() ? null
                            : f.path("target_reduction_pct").asDouble(),
                    f.path("currency").asText("INR"),
                    dbl(f, "electricity_tariff_inr_per_kwh"),
                    dbl(f, "diesel_price_inr_per_litre"),
                    dbl(f, "gas_price_inr_per_m3"),
                    dbl(f, "lpg_price_inr_per_kg"),
                    dbl(f, "waste_disposal_cost_inr_per_tonne"));

            Dtos.FactoryResponse created = service.create(req, null);
            Factory entity = factories.findById(created.id()).orElseThrow();
            entity.setDemo(true);
            factories.save(entity);

            List<Dtos.EnergyRequest> energy = new ArrayList<>();
            for (JsonNode n : root.path("energy")) {
                energy.add(new Dtos.EnergyRequest(
                        n.path("key").asText(), n.path("quantity").asDouble(),
                        n.path("unit").asText(), n.path("period").asText("YEAR"),
                        n.path("label").asText(null), n.path("data_quality").asText("ESTIMATED"),
                        n.path("provenance").asText("DEMO_SEED")));
            }
            List<Dtos.MaterialRequest> materials = new ArrayList<>();
            for (JsonNode n : root.path("materials")) {
                materials.add(new Dtos.MaterialRequest(
                        n.path("material").asText(), n.path("material_grade").asText(null),
                        n.path("function").asText(null), n.path("quantity").asDouble(),
                        n.path("unit").asText(), n.path("period").asText("YEAR"),
                        n.path("recycled_content_pct").isMissingNode() ? null
                                : n.path("recycled_content_pct").asDouble(),
                        null, n.path("supplier_region").asText(null), null,
                        n.path("data_quality").asText("ESTIMATED"), "DEMO_SEED"));
            }
            List<Dtos.WasteRequest> waste = new ArrayList<>();
            for (JsonNode n : root.path("waste")) {
                waste.add(new Dtos.WasteRequest(
                        n.path("label").asText(), n.path("quantity").asDouble(),
                        n.path("unit").asText(), n.path("period").asText("YEAR"),
                        n.path("treatment").asText("LANDFILL"), null, null,
                        n.path("data_quality").asText("ESTIMATED"), "DEMO_SEED"));
            }
            List<Dtos.ProcessRequest> processes = new ArrayList<>();
            for (JsonNode n : root.path("processes")) {
                processes.add(new Dtos.ProcessRequest(
                        n.path("process_name").asText(), n.path("process_type").asText(null),
                        n.path("machine_type").asText(null),
                        n.path("operating_hours").isMissingNode() ? null
                                : n.path("operating_hours").asDouble(),
                        n.path("energy_share_pct").isMissingNode() ? null
                                : n.path("energy_share_pct").asDouble(),
                        null,
                        n.path("output_quantity").isMissingNode() ? null
                                : n.path("output_quantity").asDouble(),
                        n.path("output_unit").asText(null),
                        n.path("scrap_rate_pct").isMissingNode() ? null
                                : n.path("scrap_rate_pct").asDouble(),
                        n.path("operating_temp_c").isMissingNode() ? null
                                : n.path("operating_temp_c").asDouble(),
                        "ESTIMATED"));
            }

            service.replaceEnergy(created.id(), energy);
            service.replaceMaterials(created.id(), materials);
            service.replaceWaste(created.id(), waste);
            service.replaceProcesses(created.id(), processes);
            log.info("seeded demo factory '{}' ({} energy, {} material, {} waste, {} process)",
                    created.name(), energy.size(), materials.size(), waste.size(),
                    processes.size());
        };
    }

    private static Double dbl(JsonNode node, String field) {
        JsonNode v = node.path(field);
        return v.isMissingNode() || v.isNull() ? null : v.asDouble();
    }

    private JsonNode read(ObjectMapper mapper) {
        for (String candidate : CANDIDATE_PATHS) {
            Path p = Path.of(candidate);
            if (Files.exists(p)) {
                try (InputStream in = Files.newInputStream(p)) {
                    return mapper.readTree(in);
                } catch (Exception ex) {
                    log.warn("could not read {}: {}", candidate, ex.getMessage());
                }
            }
        }
        return null;
    }
}
