# Proposal

## Why

The owner's page shows each pet's birth date, and the reader has to work out the pet's age from it. PC-303 asks for the pet's age to be shown on the owner's page.

## What Changes

- The owner's page keeps each pet's birth date and adds an Age row right after Birth Date, so the rows are Name, Birth Date, Age, Type (D1).
- Age is counted from the birth date to today, the same "today" the pet validator uses: the server's date in the server's default time zone (D2).
- Age is shown in completed years from 1 year up ("3 years"), in completed months under 1 year ("5 months"), and in completed days under 1 month ("12 days") (D3).
- Completed units are counted by calendar day-of-month, not by 365-day or 30-day arithmetic; a pet born today is "0 days" (D8).
- One of a unit is singular ("1 year", "1 month", "1 day") and every other count is plural; each other language gets one/other forms through the message files, and the inexact forms of Russian and of any language with more than two plural forms are a known limit (D9).
- A pet with no stored birth date, or with a birth date later than today, shows the Age label with an empty value; the page does not fail, no placeholder is shown, and an age is never negative (D4, D5, D12).
- The age appears on the owner's page only, not on the add or edit pet forms nor anywhere else (D6).
- The word "Age" is used in the page and "years old" is avoided (D7).
- The label "Age" and the unit texts (year, month, day, each in its one and other form) are shipped as real translations, not copied English: English in the default message file `messages.properties`, real translations in the 9 translated files (de, es, fa, hi, ja, ko, pt, ru, tr), all in this change (D10, D13, D14).
- `messages_en.properties` stays empty and English falls back to the default file; English is not copied into it (D14).

## Capabilities

### New Capabilities

### Modified Capabilities
- `pets` (`openspec/specs/pets/spec.md`): new requirements for the age shown on the owner's page (D11).

## Impact

- Code and pages: the owner's page (`src/main/resources/templates/owners/ownerDetails.html`); the message files in `src/main/resources/messages/`: the new label and unit texts in `messages.properties` and in the 9 translated files, with `messages_en.properties` left empty (`I18nPropertiesSyncTest` holds the translated files to every key of the default file).
- Pins changed by decisions:
  - `OwnerDetailsPageCharacterizationTests#theOwnersPageShowsNameBirthDateAndTypeInThatOrder` (D1): the order becomes Name, Birth Date, Age, Type.
  - `OwnerDetailsPageCharacterizationTests#theOwnersPageShowsAnEmptyBirthDateForAPetWithNoStoredBirthDate` (D4, D12): the Age label shows with an empty value next to the empty Birth Date.
- Pins kept as they are: the birth date as year-month-day, the visits list, the order of the pets, the links to edit a pet and add a visit, `PetControllerCharacterizationTests#todayIsAcceptedOnTheAddForm` and `PetControllerCharacterizationTests#emptyBirthDateOnTheEditForm`.

## Decisions with no scenario

- **D11** Where the requirement is filed: it goes into the existing `pets` spec, not into a new `owners` capability.
