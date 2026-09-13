package ai.ecoforge;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;

/**
 * Every Spring Data repository in this application is declared as a nested
 * interface inside {@code ai.ecoforge.repository.Repositories}. Spring Data
 * skips nested repository interfaces unless it is told not to, so
 * {@code considerNestedRepositories} is required here - without it no
 * repository bean is registered at all.
 */
@SpringBootApplication
@ConfigurationPropertiesScan
@EnableJpaRepositories(
        basePackages = "ai.ecoforge.repository",
        considerNestedRepositories = true)
public class EcoForgeApplication {
    public static void main(String[] args) {
        SpringApplication.run(EcoForgeApplication.class, args);
    }
}