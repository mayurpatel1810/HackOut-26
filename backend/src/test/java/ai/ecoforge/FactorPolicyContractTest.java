package ai.ecoforge;

import static org.assertj.core.api.Assertions.assertThat;

import ai.ecoforge.dto.Dtos;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * Contract tests for the request layer.
 *
 * These run without a database or the AI service: they assert that invalid
 * activity data is rejected by the API before it can ever reach a calculation
 * (Master Spec section 66).
 */
class FactorPolicyContractTest {

    private final Validator validator =
            Validation.buildDefaultValidatorFactory().getValidator();

    @Test
    void negativeQuantityIsRejectedWithAHumanMessage() {
        var req = new Dtos.EnergyRequest("ELECTRICITY", -5.0, "kWh", "YEAR",
                null, "INVOICED", "MANUAL");
        var violations = validator.validate(req);
        assertThat(violations).isNotEmpty();
        assertThat(violations.iterator().next().getMessage())
                .contains("cannot be negative");
    }

    @Test
    void missingUnitIsRejectedRatherThanGuessed() {
        var req = new Dtos.EnergyRequest("ELECTRICITY", 480000.0, "  ", "YEAR",
                null, "INVOICED", "MANUAL");
        assertThat(validator.validate(req)).isNotEmpty();
    }

    @Test
    void validEnergyRowPasses() {
        var req = new Dtos.EnergyRequest("ELECTRICITY", 480000.0, "kWh", "YEAR",
                "Main meter", "INVOICED", "MANUAL");
        assertThat(validator.validate(req)).isEmpty();
    }

    @Test
    void factoryRequiresNameAndIndustry() {
        var bad = new Dtos.FactoryRequest("", "", null, "IN", null, null, null,
                2026, null, null, null, null, null, null, "INR");
        assertThat(validator.validate(bad)).hasSizeGreaterThanOrEqualTo(2);
    }

    @Test
    void wasteRequiresATreatmentRouteBecauseItChangesTheFactor() {
        var bad = new Dtos.WasteRequest("Spent sand", 240.0, "tonnes", "YEAR",
                "", null, null, "ESTIMATED", "MANUAL");
        assertThat(validator.validate(bad)).isNotEmpty();
    }

    @Test
    void bulkPayloadValidatesEveryNestedRow() {
        var bulk = new Dtos.BulkActivityRequest(
                List.of(new Dtos.EnergyRequest("ELECTRICITY", -1.0, "kWh", "YEAR",
                        null, "INVOICED", "MANUAL")),
                List.of(), List.of(), List.of());
        assertThat(validator.validate(bulk)).isNotEmpty();
    }
}
