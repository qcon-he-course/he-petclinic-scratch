# The image the release workflow builds, from the jar the build has just made and tested.
# Nothing is compiled here: one build, one artifact, and the attestation names it.
FROM eclipse-temurin:17-jre
RUN useradd --system --uid 10001 --no-create-home app
COPY target/spring-petclinic-*.jar /app/app.jar
USER app
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
