package ai.ecoforge.service;

import ai.ecoforge.config.EcoForgeProperties;
import ai.ecoforge.exception.AiServiceUnavailableException;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.Duration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

/**
 * The only route from Spring Boot to the Python AI/ML service.
 *
 * Analysis payloads pass through as JSON rather than being re-modelled in Java.
 * That is deliberate: the deterministic engine is the single source of
 * numerical truth, and mirroring its output into Java DTOs would create a
 * second definition of the same numbers that could drift.
 */
@Component
public class AiServiceClient {

    private static final Logger log = LoggerFactory.getLogger(AiServiceClient.class);

    private final RestClient client;
    private final String token;

    public AiServiceClient(EcoForgeProperties props) {
        var factory = new SimpleClientHttpRequestFactory();
        var timeout = Duration.ofSeconds(props.getAiService().getTimeoutSeconds());
        factory.setConnectTimeout((int) Duration.ofSeconds(10).toMillis());
        factory.setReadTimeout((int) timeout.toMillis());
        this.token = props.getAiService().getToken();
        this.client = RestClient.builder()
                .baseUrl(props.getAiService().getBaseUrl())
                .requestFactory(factory)
                .defaultHeader("Content-Type", MediaType.APPLICATION_JSON_VALUE)
                .build();
    }

    public JsonNode post(String path, Object body) {
        try {
            var spec = client.post().uri(path).body(body);
            if (token != null && !token.isBlank()) {
                spec = spec.header("Authorization", "Bearer " + token);
            }
            JsonNode node = spec.retrieve().body(JsonNode.class);
            if (node == null) {
                throw new AiServiceUnavailableException(
                        "The analysis service returned an empty response.");
            }
            return node;
        } catch (ResourceAccessException ex) {
            log.error("AI service unreachable at {}: {}", path, ex.getMessage());
            throw new AiServiceUnavailableException(
                    "EcoForge could not reach the analysis service, so nothing was "
                    + "calculated and nothing was saved. Please try again in a moment.");
        } catch (RestClientResponseException ex) {
            log.error("AI service error {} at {}: {}", ex.getStatusCode(), path,
                    ex.getResponseBodyAsString());
            throw new AiServiceUnavailableException(
                    "The analysis service rejected this request. Check that every "
                    + "activity has a supported unit and a quantity.");
        }
    }

    public JsonNode get(String path) {
        try {
            var spec = client.get().uri(path);
            if (token != null && !token.isBlank()) {
                spec = spec.header("Authorization", "Bearer " + token);
            }
            JsonNode node = spec.retrieve().body(JsonNode.class);
            if (node == null) {
                throw new AiServiceUnavailableException(
                        "The analysis service returned an empty response.");
            }
            return node;
        } catch (ResourceAccessException ex) {
            throw new AiServiceUnavailableException(
                    "EcoForge could not reach the analysis service right now.");
        } catch (RestClientResponseException ex) {
            throw new AiServiceUnavailableException(
                    "The analysis service could not complete this request.");
        }
    }
}
