# Design

## Context

See proposal.md for why, and `specs/pets/spec.md` for the behaviour. The facts this design relies on:

- The owner's page is `owners/ownerDetails.html`, rendered only by `OwnerController.showOwner` (`OwnerController.java`, lines 178-186). Each pet's details are a `<dl>` of Name, Birth Date and Type (`ownerDetails.html`, lines 50-57). The birth date is written with `#temporals.format(pet.birthDate, 'yyyy-MM-dd')`.
- The pet forms take today as `LocalDate.now()` (`PetValidator.java`, line 61), which is the date in the JVM's default time zone (D11).
- `Pet.birthDate` is a nullable `LocalDate` (`Pet.java`, lines 48-50).
- Messages come from `messages/messages*.properties` (`application.properties`, line 16). The language is chosen with `?lang=` and kept in the session, English by default (`WebConfiguration.java`, lines 32-58).
- `I18nPropertiesSyncTest` fails if a translated file lacks a key of `messages.properties` (it skips `messages_en.properties`), or if a template line has literal text with no `#{` or `th:text` (lines 39-136).
- `ArchitectureTests` forbids controllers from calling `Errors.rejectValue`. This change does not touch validation.
- Pitest mutates `PetController` and `PetValidator` with the tests `owner.Pet*Tests` (`pom.xml`, lines 320-344).

## Goals / Non-Goals

**Goals:**

- One calculation, from a birth date and today to an age. It can be unit-tested with fixed dates and checks every scenario marked unit without Spring.
- The page passes in today. The calculation never reads the clock itself.

**Non-Goals:**

- A `Clock` bean or any setting for today (D11: no new setting).
- Translated texts and plural rules for other languages (D7: a later translation ticket).
- Storing the age, or any schema change (D2).

## Decisions

### A `PetAge` value in the `owner` package

A small immutable type `PetAge` holds a message code and a count, with a factory `PetAge.of(LocalDate birthDate, LocalDate today)`. The factory returns an empty `Optional` when the birth date is missing or after today (D4, D9). `Pet.ageOn` (below) unwraps it to `null` for the template. Otherwise:

- whole years = `ChronoUnit.YEARS.between(birthDate, today)`. If it is 1 or more: code `age.year` (1) or `age.years` (N).
- otherwise whole months = `ChronoUnit.MONTHS.between(birthDate, today)`. If it is 1 or more: code `age.month` or `age.months`.
- otherwise code `age.underAMonth`.

`ChronoUnit.MONTHS/YEARS.between` on `LocalDate` drops a month when the end's day of month is lower than the start's. That should give D3's and D8's rule: 2024-02-29 to 2025-02-28 is 11 months, and to 2025-03-01 it is 12 months. 2026-01-31 to 2026-02-28 is 0 months, and to 2026-03-01 it is 1 month. **INFERRED** from the JDK's documented `LocalDate.until` behaviour. It has not been run here. The unit scenarios for 29 February and 31 January are what pin it. If any fails, write the rule out by hand rather than change the scenario.

*Alternatives:* a method on `Pet` that reads `LocalDate.now()` itself. Rejected: it cannot be tested at unit level for fixed dates. `Period.between`: the same arithmetic, but splitting it into years and months adds nothing here.

### Today comes from the controller, into the template

`showOwner` adds `today` = `LocalDate.now()` to the model. This is the same call as `PetValidator` (D11). `Pet` gets `ageOn(LocalDate today)`, which delegates to `PetAge.of(birthDate, today)`, and the template calls `${pet.ageOn(today)}`. `Pet` gains no field, so JPA and the schema are unchanged (D2).

*Alternative:* a static call from the template (`T(...)`). Rejected: it is harder to read, and it is the controller that should own today.

### Texts as message keys, resolved by the template

Keys in `messages.properties`: `age=Age`, `age.year=1 year`, `age.years={0} years`, `age.month=1 month`, `age.months={0} months`, `age.underAMonth=under a month`. The same English lines go into each translated file (D7), but not into `messages_en.properties`, which stays empty and falls back to `messages.properties` (D14). The template writes the label with `th:text="#{age}"` and the value with the message for the code and count, or an empty `<dd>` when there is no age (D10), directly after the birth date's `<dd>` and before Type (D13). Writing it this way also keeps `checkNonInternationalizedStrings` passing.

The age always uses the digits 0 to 9 (D16), so the template passes the count as a string and `MessageFormat` does not format it for the page's language.

### Unit tests resolve the real texts

`PetAgeTests` (plain JUnit, no Spring test annotation, so unit level) builds a `ResourceBundleMessageSource` with base name `messages/messages` and resolves each `PetAge` in English. Its assertions are the scenario texts ("3 years"), not message codes. The class name matches pitest's `Pet*Tests`, but `PetAge` is not added to pitest's `targetClasses`: this change leaves `pom.xml` as it is (D17).

### Form tests in `OwnerControllerTests`

The four form scenarios go into `OwnerControllerTests`, which is `@WebMvcTest(OwnerController.class)` and so form level. They read the rendered HTML. Whether `@WebMvcTest` loads the message source and `WebConfiguration` is **INFERRED**: no test reads rendered text today (no `content().string` in `src/test`). Task 3.1 checks it first.

For the time zone scenario, the test chooses, when it runs, a zone where the date differs from UTC's, and sets `TimeZone.setDefault` to it (D18). No zone is a day ahead of UTC before 10:00 UTC, so it takes `Pacific/Kiritimati` (14 hours ahead) when that zone's date is later than UTC's, and otherwise `Pacific/Pago_Pago` (11 hours behind, so a day behind until 11:00 UTC). It first asserts that the two dates differ. The pet is born on the later of the two dates: with the zone ahead, the page shows "under a month", where UTC's date would make the birth date after today and show no age; with the zone behind, the birth date is after the server's today and the page shows no age (D9), where UTC's date would show "under a month". It restores the previous default in a `finally` block.

## Risks / Trade-offs

- [A form test computes `LocalDate.now()` and the server computes it again; across midnight they differ by a day] → The test uses a birth date exactly N years back and accepts no other value. A run across midnight is rare. If it ever fails, the answer is a `Clock`, which needs a person's decision (D11 rejected a new setting, and a bean may count as one).
- [`TimeZone.setDefault` is global to the JVM] → Restore it in `finally`. Tests run one at a time in this build: `pom.xml` has no `surefire`, `parallel` or `forkCount` setting, and there is no `src/test/resources/junit-platform.properties` (VERIFIED by search). If parallel runs are turned on later, this test needs `@Isolated`.
- [Two keys per unit (one/many) do not fit languages with more plural forms, such as Russian] → Leave it to the translation ticket. It can move to ICU plural messages without changing the specs.
- [`ChronoUnit` arithmetic might not match D8 in some case the scenarios do not cover] → The scenarios include D3's and D8's own examples. Pitest is not run on `PetAge` in this change (D17), so boundaries the tests do not pin stay unmeasured until Week 4's mutation testing of new classes.

## Migration Plan

None. Nothing is stored, and rolling back is reverting the commit.
