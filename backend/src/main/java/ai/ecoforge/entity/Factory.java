package ai.ecoforge.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.NotBlank;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "factories")
public class Factory {

    @Id
    @GeneratedValue
    private UUID id;

    @Column(name = "owner_id")
    private UUID ownerId;

    @NotBlank
    private String name;

    @NotBlank
    private String industry;

    @Column(name = "production_type")
    private String productionType;

    @Column(name = "country_code", nullable = false)
    private String countryCode = "IN";

    @Column(name = "state_or_region")
    private String stateOrRegion;

    private String city;

    @Column(name = "grid_region")
    private String gridRegion;

    @Column(name = "is_demo", nullable = false)
    private boolean demo = false;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt = Instant.now();

    @OneToOne(mappedBy = "factory", cascade = CascadeType.ALL, orphanRemoval = true)
    private FactoryProfile profile;

    @PreUpdate
    void touch() { this.updatedAt = Instant.now(); }

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }
    public UUID getOwnerId() { return ownerId; }
    public void setOwnerId(UUID ownerId) { this.ownerId = ownerId; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
    public String getIndustry() { return industry; }
    public void setIndustry(String industry) { this.industry = industry; }
    public String getProductionType() { return productionType; }
    public void setProductionType(String productionType) { this.productionType = productionType; }
    public String getCountryCode() { return countryCode; }
    public void setCountryCode(String countryCode) { this.countryCode = countryCode; }
    public String getStateOrRegion() { return stateOrRegion; }
    public void setStateOrRegion(String stateOrRegion) { this.stateOrRegion = stateOrRegion; }
    public String getCity() { return city; }
    public void setCity(String city) { this.city = city; }
    public String getGridRegion() { return gridRegion; }
    public void setGridRegion(String gridRegion) { this.gridRegion = gridRegion; }
    public boolean isDemo() { return demo; }
    public void setDemo(boolean demo) { this.demo = demo; }
    public Instant getCreatedAt() { return createdAt; }
    public void setCreatedAt(Instant createdAt) { this.createdAt = createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(Instant updatedAt) { this.updatedAt = updatedAt; }
    public FactoryProfile getProfile() { return profile; }
    public void setProfile(FactoryProfile profile) { this.profile = profile; }
}
