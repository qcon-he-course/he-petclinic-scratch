# Tasks

Test naming, for every test below. A test shows its scenario by its method name alone, with no comment. The name is the scenario's title in lowerCamelCase, with punctuation and apostrophes dropped, and more words may follow. A test's level comes from its class: a class with no Spring test annotation is unit, and `@WebMvcTest` is form. Each scenario's test sits in a class of the level on its `CHECKED AT` line.

## 1. Open questions

- [x] 1.1 Get a person's answers to Q1 (which side of the birth date), Q2 (`messages_en.properties`), Q3 (the `pets` spec's Purpose) and Q4 (digits) in proposal.md. Verify: each is recorded as a new decision in `decisions.md`, in the log's existing format, and proposal.md, specs and these tasks are updated to match. Then `openspec validate pc-303 --strict` passes.

## 2. The age calculation and its texts

- [x] 2.1 Add the age keys to `src/main/resources/messages/messages.properties` (`age`, `age.year`, `age.years`, `age.month`, `age.months`, `age.underAMonth`, English text as in design.md). Add the same English lines to `messages_de`, `_es`, `_fa`, `_hi`, `_ja`, `_ko`, `_pt`, `_ru` and `_tr`. `messages_en.properties` stays as it is (D14). Verify: `./mvnw test -Dtest=I18nPropertiesSyncTest` passes, with that test unchanged (`git diff` shows no change to it), and `git diff -- src/main/resources/messages/messages_en.properties` is empty.
- [x] 2.2 Add `PetAge` in `org.springframework.samples.petclinic.owner`, with `PetAge.of(LocalDate birthDate, LocalDate today)` as in design.md. It does not read the clock. Verify: task 2.3's tests pass.
- [x] 2.3 Add `PetAgeTests` in `src/test/java/org/springframework/samples/petclinic/owner/` with no Spring test annotation (unit). It resolves texts through a `ResourceBundleMessageSource` on `messages/messages` in English, and has one test per unit scenario, named: `aPetOneYearOld`, `aPetThreeYearsOld`, `theDayBeforeABirthday`, `wholeYearsOnlyFromOneYearOn`, `aPetOneMonthOld`, `aPetFiveMonthsOld`, `theDayBeforeTheFirstBirthday`, `aPetBornToday`, `theDayBeforeTheFirstMonth`, `bornOn29FebruaryBefore1MarchInAYearWithoutOne`, `bornOn29FebruaryOn1MarchInAYearWithoutOne`, `bornOn29FebruaryInALeapYear`, `bornOn31JanuaryAtTheEndOfFebruary`, `bornOn31JanuaryOn1March`, `noStoredBirthDate`, `aBirthDateAfterToday`. Each uses the scenario's own dates and asserts its exact text, or no age. Verify: `./mvnw test -Dtest=PetAgeTests` passes with 16 tests.
- [x] 2.4 `PetAge` is not in pitest's `targetClasses` in this change, and `pom.xml` stays as it was at the start of the change (D17): any `pom.xml` change makes the risk floor material, and mutation testing of new classes is Week 4's work, with its thresholds before commit. Verify: `git diff -- pom.xml` is empty; `./mvnw validate` passes.

## 3. The owner's page

- [x] 3.1 Before any page change, check that `@WebMvcTest(OwnerController.class)` renders message texts and honours `?lang=`. Do this with a throwaway assertion in `OwnerControllerTests` that `GET /owners/1?lang=de` contains the German `ownerInformation` text, then remove it. Verify: the assertion passed. If it did not, stop and report: the form scenarios would need another test setup, which is a person's call.
- [x] 3.2 Add `Pet.ageOn(LocalDate today)` delegating to `PetAge.of`, with no new field. In `OwnerController.showOwner`, add `today` = `LocalDate.now()` to the model. In `owners/ownerDetails.html`, add `<dt th:text="#{age}">` and a `<dd>` with the age text, or empty when there is none, directly after the birth date's `<dd>` and before Type (D13). The count is passed to the message as a string, so it is written with the digits 0 to 9 (D16). Verify: task 3.3's tests pass, and `git diff` shows no change to `src/main/resources/db/`.
- [x] 3.3 Add to `OwnerControllerTests` (`@WebMvcTest`, form) one test per form scenario, named: `theAgeIsShownDirectlyAfterTheBirthDate`, `aPetWithNoAgeStillShowsTheLabel`, `todayIsTheDateInTheServersTimeZone` (sets and restores `TimeZone.setDefault` as in design.md), and `theAgeTextsInTheOtherLanguages` (a parameterized test over de, es, fa, hi, ja, ko, pt, ru and tr, asserting the digits 0 to 9, D16). Each asserts on the rendered HTML: "Age" in the pet's `<dt>`, and the age text, or an empty `<dd>`, directly after the birth date and before Type. Verify: `./mvnw test -Dtest=OwnerControllerTests` passes, including the existing `showOwner`.

## 4. Integration checks

- [x] 4.1 Run `./mvnw spring-javaformat:apply`, then `./mvnw validate`. Verify: validate passes (formatting and nohttp).
- [x] 4.2 Run `./mvnw test`. Verify: the whole suite passes, including `ArchitectureTests` and `I18nPropertiesSyncTest`.
- [x] 4.3 Check scenario-to-test coverage. Verify: each of the 20 scenarios in `specs/pets/spec.md` has a test whose method name starts with the scenario title in lowerCamelCase, in a class of the level on its `CHECKED AT` line (16 in `PetAgeTests`, 4 in `OwnerControllerTests`). No test carries a comment naming its scenario.
- [x] 4.4 Run `openspec validate pc-303 --strict`. Verify: it passes.

## 5. The gate after round 3 (`.review-inputs/gate.md`, 2 November)

- [x] 5.1 (W1) `todayIsTheDateInTheServersTimeZone` chooses, when it runs, a zone whose date differs from UTC's (`Pacific/Kiritimati` when UTC's time allows, otherwise `Pacific/Pago_Pago`), first asserts that the two dates differ, and uses a birth date for which the two dates give different pages. Replace the scenario's WHEN, THEN and CHECKED AT lines with the text the gate after round 4 gives (`.review-inputs/gate.md`, W1, D18), changing nothing else in the spec delta, and keep design.md's line on the comparison to match. Verify: `openspec validate pc-303 --strict` is valid; `./mvnw test -Dtest=OwnerControllerTests` passes; with the controller using UTC's date, the test fails; the self-review says why it fails at every hour, for both zones.
- [x] 5.2 (W2) `theAgeTextsInTheOtherLanguages` also asserts, for each language, the owner-information heading from that language's file, beside the English age text. Verify: `./mvnw test -Dtest=OwnerControllerTests` passes; with `?lang=` ignored, the test fails.

## Workflow follow-up

- Archive the change once it has been reviewed. The `pets` spec's Purpose was widened by editing `openspec/specs/pets/spec.md` directly (D15): archiving does not change the Purpose.
