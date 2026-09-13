# ---- build ----
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /build
COPY backend/pom.xml ./pom.xml
RUN mvn -B -q dependency:go-offline
COPY backend/src ./src
RUN mvn -B -q -DskipTests package

# ---- run ----
FROM eclipse-temurin:21-jre-alpine
WORKDIR /srv
RUN addgroup -S app && adduser -S app -G app && apk add --no-cache curl
COPY --from=build /build/target/*.jar app.jar
COPY database/migrations /srv/database/migrations
COPY data/curated /srv/data/curated
USER app
ENV FLYWAY_LOCATIONS=filesystem:/srv/database/migrations \
    JAVA_OPTS="-XX:MaxRAMPercentage=70"
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD curl -fsS http://localhost:8080/actuator/health || exit 1
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
