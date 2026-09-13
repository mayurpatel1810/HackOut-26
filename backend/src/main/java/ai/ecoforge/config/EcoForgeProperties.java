package ai.ecoforge.config;

import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

/** Typed view of the ecoforge.* configuration block. Nothing here has a secret default. */
@ConfigurationProperties(prefix = "ecoforge")
public class EcoForgeProperties {

    private AiService aiService = new AiService();
    private Security security = new Security();
    private Demo demo = new Demo();

    public AiService getAiService() { return aiService; }
    public void setAiService(AiService aiService) { this.aiService = aiService; }
    public Security getSecurity() { return security; }
    public void setSecurity(Security security) { this.security = security; }
    public Demo getDemo() { return demo; }
    public void setDemo(Demo demo) { this.demo = demo; }

    public static class AiService {
        private String baseUrl = "http://localhost:8001";
        private String token = "";
        private int timeoutSeconds = 90;

        public String getBaseUrl() { return baseUrl; }
        public void setBaseUrl(String baseUrl) { this.baseUrl = baseUrl; }
        public String getToken() { return token; }
        public void setToken(String token) { this.token = token; }
        public int getTimeoutSeconds() { return timeoutSeconds; }
        public void setTimeoutSeconds(int timeoutSeconds) { this.timeoutSeconds = timeoutSeconds; }
    }

    public static class Security {
        private String jwtSecret = "";
        private int jwtTtlMinutes = 720;
        private List<String> corsOrigins = List.of("http://localhost:5173");

        public String getJwtSecret() { return jwtSecret; }
        public void setJwtSecret(String jwtSecret) { this.jwtSecret = jwtSecret; }
        public int getJwtTtlMinutes() { return jwtTtlMinutes; }
        public void setJwtTtlMinutes(int jwtTtlMinutes) { this.jwtTtlMinutes = jwtTtlMinutes; }
        public List<String> getCorsOrigins() { return corsOrigins; }
        public void setCorsOrigins(List<String> corsOrigins) { this.corsOrigins = corsOrigins; }
    }

    public static class Demo {
        private boolean seedOnStartup = true;
        public boolean isSeedOnStartup() { return seedOnStartup; }
        public void setSeedOnStartup(boolean seedOnStartup) { this.seedOnStartup = seedOnStartup; }
    }
}
