# PetClinic project baseline: architecture and conventions

What every change to this repository is held to, beyond the spec of the slice it touches. Every line cites the code. A change that departs from a line here needs a decision in its log that says so, and a reviewer reports a departure without one.

Requirements live in `openspec/specs/` (so far only `pets`). Verified facts about the code are in `AGENTS.md`.

## Architecture

- **A1. Pets and visits are reached through their owner.** There is no repository for pets or visits: the repositories are `OwnerRepository`, `PetTypeRepository` and `VetRepository`. `PetController` and `VisitController` load the `Owner` through `OwnerRepository`, change its pets or visits, and save the owner; JPA cascades from `Owner.pets` to `Pet.visits` write the rows. (`owner/Owner.java:67-70`, `owner/Pet.java:56`, `owner/PetController.java:120, 190`, `owner/VisitController.java:109`)
- **A2. Field validation belongs in the form's validator, not the controller.** Enforced by the frozen ArchUnit rule `controllersLeaveFieldValidationToValidators`: no `@Controller` calls `Errors.rejectValue`; the existing calls in `PetController` are frozen in `src/test/resources/archunit_store/`, and a new one fails the build. (`ArchitectureTests.java:36-43`)
- **A3. The schema comes from SQL scripts, not from Hibernate.** `spring.sql.init` runs `db/${database}/schema.sql` and `data.sql` (H2 by default; `mysql` and `postgres` profiles); `ddl-auto=none`, `open-in-view=false`. There is no migration tool. (`application.properties:2-4, 10-11`)
- **A4. Uniqueness is enforced by the database as well as the code.** All three schemas have a unique constraint on owner and pet name: H2's and Postgres's are named `unique_owner_pet_name`, Postgres's on `LOWER(name)`; MySQL's is unnamed. In H2 the name column is `VARCHAR_IGNORECASE`. (`db/h2/schema.sql:48, 55`, `db/postgres/schema.sql:45`, `db/mysql/schema.sql:47`)

## Conventions the build enforces

- **B1. Formatting and URLs.** `./mvnw verify` fails on unformatted code (`spring-javaformat`) and on any plain `http://` URL (nohttp checkstyle). (`pom.xml:213, 235-248`)
- **B2. No hard-coded text, and every message key in every language.** `I18nPropertiesSyncTest` fails if a template has hard-coded text or a key is missing from a `messages_*.properties` file. (`system/I18nPropertiesSyncTest.java:40, 87`)
- **B3. A test is named after the scenario it shows.** The method's name is the scenario's title in lowerCamelCase; its level comes from its class. The scenario-coverage check reads both. (`openspec/specs/pets/spec.md`, `owner/PetControllerCharacterizationTests.java`)

## Known defects

- **PC-302.** Two pets added to one owner at the same moment can lose one; the race test `PetClinicConcurrencyTests.twoSimultaneousAddsWithTheSameName` passes or fails by timing. It sits in A1's save-the-owner pattern. While the ticket is open, the test runs in the pipeline's known-defect lane: shown, not counted.
