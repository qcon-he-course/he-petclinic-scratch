# Decisions: item-12

Item: #12 PC-303

## Decided

- **D1** The owner's page keeps each pet's birth date and adds the pet's age as a new row right after Birth Date, so the order becomes Name, Birth Date, Age, Type. Changes pin: OwnerDetailsPageCharacterizationTests#theOwnersPageShowsNameBirthDateAndTypeInThatOrder. Asked as Q1, answered 2026-11-23. Rejected: replacing the birth date with the age.
- **D2** Age is counted from the birth date to today, where today is the same "today" the pet validator uses (`LocalDate.now()`, the server's default time zone). Asked as Q2, answered 2026-11-23.
- **D3** Age is shown in completed years when the pet is 1 year old or more ("3 years"), in completed months when under 1 year ("5 months"), and in completed days when under 1 month ("12 days"). Asked as Q3, answered 2026-11-23. Rejected: years and months together everywhere ("2 years 3 months").
- **D4** For a pet with no stored birth date, the Age cell is empty, like the Birth Date cell; the page must not fail. Changes pin: OwnerDetailsPageCharacterizationTests#theOwnersPageShowsAnEmptyBirthDateForAPetWithNoStoredBirthDate. Asked as Q4, answered 2026-11-23. Rejected: a placeholder such as "unknown".
- **D5** For a stored birth date later than today, the Age cell is empty; an age is never negative. Asked as Q5, answered 2026-11-23. Rejected: showing "0 days".
- **D6** The age appears on the owner's page only, not on the add or edit pet forms nor anywhere else. Asked as Q6, answered 2026-11-23.
- **D7** The team's word is "Age", defined in the glossary; "years old" is avoided. Asked as Q7, answered 2026-11-23.
- **D8** "Completed" is counted by calendar day-of-month: born 2025-01-31 and today 2025-02-28 is "28 days"; born 2024-02-29 is "11 months" on 2025-02-28 and "1 year" on 2025-03-01; born 2025-11-23 is "11 months" on 2026-11-22 and "1 year" on 2026-11-23; born today is "0 days". Asked as Q8, answered 2026-11-23. Rejected: 365-day or 30-day arithmetic.
- **D9** One of a unit is singular ("1 year", "1 month", "1 day") and every other count is plural ("0 days", "2 years"). English must be exact; each other language gets one/other forms through the message files, and the inexact forms in Russian (and any language with more than two plural forms) are accepted as a known limit. Asked as Q9, answered 2026-11-23. Rejected: a plural library such as ICU4J; a unit-neutral form.
- **D10** The change ships real translations of the label "Age" and of the unit texts, not English copied into them: English in the default file `messages.properties`, real translations in the 9 translated files (de, es, fa, hi, ja, ko, pt, ru, tr). Asked as Q10, answered 2026-11-23; count corrected by D14 on 2026-11-25 (was "all 11 message files").
- **D11** The age requirement goes into the existing `pets` spec as a new requirement, not into a new `owners` capability. Asked as Q11, answered 2026-11-23. Rejected: a new `owners` capability.
- **D12** When a pet has no age (D4, D5), the "Age" label still shows, with an empty value; the row is never left out, so every pet shows the same rows in the same order. Changes pin: OwnerDetailsPageCharacterizationTests#theOwnersPageShowsAnEmptyBirthDateForAPetWithNoStoredBirthDate. Asked as Q12, answered 2026-11-23. Rejected: leaving the Age row out.
- **D13** D10 stands: the label and the unit texts are translated into all 9 other languages in this change, not left in English until a translation item. Asked as Q13, answered 2026-11-23; count corrected by D14 on 2026-11-25 (was "all 10 other languages"). Rejected: English placeholders in every file until a later translation item.
- **D14** English goes in `messages.properties` only; `messages_en.properties` stays empty and falls back to the default; the 9 other files (de, es, fa, hi, ja, ko, pt, ru, tr) get real translations, so the count in D10 and D13 is 9, not 10. Asked as Q14, answered 2026-11-25. Rejected: copying English into `messages_en.properties`.

## Facts the decisions rest on

- **F1** The owner's page shows each pet's name, birth date (yyyy-MM-dd) and type, in that order. Source: `src/main/resources/templates/owners/ownerDetails.html:52-56`, `OwnerDetailsPageCharacterizationTests#theOwnersPageShowsNameBirthDateAndTypeInThatOrder`.
- **F2** The pet validator rejects a birth date after `LocalDate.now()` only at save time; a birth date of today is accepted, so a pet can be 0 days old. Source: `src/main/java/org/springframework/samples/petclinic/owner/PetValidator.java:61`, `PetControllerCharacterizationTests#todayIsAcceptedOnTheAddForm`.
- **F3** No `Clock` bean exists; the code reads today with `LocalDate.now()`. Source: `PetValidator.java:61`, `VisitController.java:85, 100`.
- **F4** The schema and the entity allow a pet with no birth date, and today the owner's page shows an empty Birth Date cell for it. Source: `src/main/resources/db/h2/schema.sql:49`, `owner/Pet.java:50`, `OwnerDetailsPageCharacterizationTests#theOwnersPageShowsAnEmptyBirthDateForAPetWithNoStoredBirthDate`.
- **F5** The sample pets were born between 2010 and 2012. Source: `src/main/resources/db/h2/data.sql:36-43`.
- **F6** Every message key in the default file `messages.properties` must be in each of the 9 translated message files, and templates must not hold hard-coded text; `messages_en.properties` is empty and the sync test skips it, because English falls back to the default file. Source: `docs/project-baseline.md` B2, `I18nPropertiesSyncTest.java:117-119`.
- **F7** Spring's message files use `MessageFormat`, whose choice format gives a one/other choice but cannot express three plural forms such as Russian's. Source: `src/main/resources/messages/messages_ru.properties`, Spring `MessageSource`.

## Open

