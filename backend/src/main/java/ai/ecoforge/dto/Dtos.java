package ai.ecoforge.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import jakarta.validation.constraints.Size;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/** Request and response shapes for the business API. */
public final class Dtos {
    private Dtos() { }

    // --- auth ---------------------------------------------------------------
    public record RegisterRequest(
            @Email(message = "Enter a valid email address.") @NotBlank String email,
            @NotBlank @Size(min = 10, message = "Use at least 10 characters.") String password,
            @NotBlank String displayName) { }

    public record LoginRequest(@Email @NotBlank String email, @NotBlank String password) { }

    public record AuthResponse(String token, String displayName, String role,
                               long expiresInSeconds) { }

    // --- factory ------------------------------------------------------------
    public record FactoryRequest(
            @NotBlank(message = "Give the factory a name.") String name,
            @NotBlank(message = "Choose an industry so EcoForge can find relevant alternatives.") String industry,
            String productionType,
            @NotBlank String countryCode,
            String stateOrRegion,
            String city,
            String gridRegion,
            @NotNull Integer reportingYear,
            @PositiveOrZero Double annualProduction,
            String productionUnit,
            Integer employees,
            Double floorAreaM2,
            @PositiveOrZero Double annualBudgetInr,
            Double targetReductionPct,
            String currency,
            // Prices the factory supplies. Without them EcoForge reports
            // "verified data unavailable" rather than assuming a tariff.
            @PositiveOrZero Double electricityTariffInrPerKwh,
            @PositiveOrZero Double dieselPriceInrPerLitre,
            @PositiveOrZero Double gasPriceInrPerM3,
            @PositiveOrZero Double lpgPriceInrPerKg,
            @PositiveOrZero Double wasteDisposalCostInrPerTonne) { }

    public record FactoryResponse(UUID id, String name, String industry, String productionType,
                                  String countryCode, String stateOrRegion, String city,
                                  String gridRegion, boolean demo, Integer reportingYear,
                                  Double annualProduction, String productionUnit,
                                  Integer employees, Double floorAreaM2,
                                  Double annualBudgetInr, Double targetReductionPct,
                                  String currency,
                                  Double electricityTariffInrPerKwh,
                                  Double dieselPriceInrPerLitre,
                                  Double gasPriceInrPerM3,
                                  Double lpgPriceInrPerKg,
                                  Double wasteDisposalCostInrPerTonne) { }

    // --- activity data ------------------------------------------------------
    public record EnergyRequest(
            @NotBlank(message = "Pick an energy type.") String energyType,
            @NotNull @PositiveOrZero(message = "A quantity cannot be negative.") Double quantity,
            @NotBlank(message = "A unit is required - EcoForge will not guess one.") String unit,
            String period, String sourceLabel, String dataQuality, String provenance) { }

    public record MaterialRequest(
            @NotBlank String material, String materialGrade, String function,
            @NotNull @PositiveOrZero Double quantity, @NotBlank String unit, String period,
            Double recycledContentPct, String supplier, String supplierRegion,
            Double unitCost, String dataQuality, String provenance) { }

    public record WasteRequest(
            @NotBlank String wasteType, @NotNull @PositiveOrZero Double quantity,
            @NotBlank String unit, String period, @NotBlank String treatment,
            Double recoveredPct, Double disposalCost, String dataQuality, String provenance) { }

    public record ProcessRequest(
            @NotBlank String processName, String processType, String machineType,
            Double operatingHours, Double energySharePct, String materialInput,
            Double outputQuantity, String outputUnit, Double scrapRatePct,
            Double operatingTempC, String dataQuality) { }

    public record BulkActivityRequest(
            List<@Valid EnergyRequest> energy,
            List<@Valid MaterialRequest> materials,
            List<@Valid WasteRequest> waste,
            List<@Valid ProcessRequest> processes) { }

    // --- analysis / decisions ----------------------------------------------
    public record AnalyseOptions(String view, Double budgetInr, Double maxPaybackYears,
                                 String minConfidence, String strictness,
                                 Map<String, Double> weights,
                                 List<Map<String, Object>> history) { }

    public record OptimiseRequest(@NotNull Double budgetInr, AnalyseOptions options) { }

    public record CurveRequest(@NotNull List<Double> budgets, AnalyseOptions options) { }

    public record SimulateRequest(@NotNull List<String> selection, AnalyseOptions options) { }

    public record CopilotRequest(@NotBlank String question, List<String> selection,
                                 Double budgetInr, AnalyseOptions options) { }

    public record ExtractRequest(@NotBlank String text) { }

    public record ApiError(String message, String detail, String requestId,
                           Map<String, String> fields) { }
}
