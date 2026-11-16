# Proposal

Ticket: PC-303 Show each pet's age on the owner's page. Every decision below is taken from `decisions.md` in this change (D1 to D17); this proposal adds none.

## Why

The owner's page shows each pet's birth date (`src/main/resources/templates/owners/ownerDetails.html`, lines 53-54), so reception has to work out the pet's age by hand. The ticket asks the page to show the age itself.

## What Changes

- The owner's page shows an "Age" entry for each pet, directly after the pet's birth date and before its type (D5, as amended by D7 and D13).
- The age is the pet's **Age** as `GLOSSARY.md` defines it (D12): whole years from one year on ("1 year", "3 years"), whole months under a year ("1 month", "5 months"), and "under a month" before that (D1).
- A birthday counts on the day itself. A pet born on 29 February has its birthday on 1 March in a year with no 29 February (D3). A month counts when its day comes. When the current month has no such day, the month counts from the 1st of the next month (D8).
- The age is worked out as of today when the page is shown. Nothing new is stored and the schema does not change (D2). "Today" is the date in the server's default time zone, the same today the pet forms use (D11).
- A pet with no stored birth date, or with a birth date after today, shows no age (D4, D9). Its "Age" entry is still shown, with an empty value (D10).
- The "Age" label and the age texts go into every language file that `I18nPropertiesSyncTest` checks, in English, until a translation ticket. `messages_en.properties` stays empty and `I18nPropertiesSyncTest` does not change (D7, D14).
- The age always uses the digits 0 to 9, as the birth date beside it does, in every language (D16).
- `pom.xml` does not change: `PetAge` is not added to pitest's targets in this change (D17).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `pets`: adds requirements for the pet's age on the owner's page. This is the baseline named for this ticket, `openspec/specs/pets/spec.md`. No existing requirement changes. The spec's Purpose said it did not cover owners, so this change widens it to cover a pet's details on the owner's page (D15). OpenSpec has no delta for a Purpose and archiving does not change it, so the change edits the Purpose line of `openspec/specs/pets/spec.md` directly. That is its one edit to the main spec.

## Impact

- Owner's page template `owners/ownerDetails.html`, and `OwnerController.showOwner`, which renders it (`OwnerController.java`, lines 178-186).
- A new calculation in the `owner` package, from a birth date and today to an age. It has unit tests.
- Message files: `messages.properties` and the nine translated files (`de`, `es`, `fa`, `hi`, `ja`, `ko`, `pt`, `ru`, `tr`). `messages_en.properties` does not change (D14).
- The Purpose line of the main spec `openspec/specs/pets/spec.md` (D15).
- No change to the database schema, the data scripts, the pet forms or `PetValidator`.
- Out of scope: other pages that show a birth date, such as the visit form (`pets/createOrUpdateVisitForm.html`, line 24). The ticket names the owner's page only.

## Open questions

All four were answered at the gate on 2026-11-02 (`.review-inputs/gate.md`); see decisions D13 to D16. The questions are kept below as they were asked.

- **Q1 Which side of the birth date?** Answered at the gate, see decisions (D13). D5 puts "Age" "next to the pet's birth date". The pet's details are a list of Name, Birth Date, Type (`ownerDetails.html`, lines 51-56). Should "Age" go directly after Birth Date, before Type, or directly before Birth Date? The specs say "next to" only, and task 3.2 waits for this answer.
- **Q2 Does `messages_en.properties` get the texts?** Answered at the gate, see decisions (D14). D7 says "every language file". `messages_en.properties` is empty on purpose: its only line says look-ups fall back to `messages.properties`. `I18nPropertiesSyncTest` skips it (lines 117-121). Either answer shows the same English text. The only difference is whether that file stays empty.
- **Q3 The `pets` spec's Purpose.** Answered at the gate, see decisions (D15). Its Purpose says it covers the pet forms and "does not cover the GET forms, owners, visits or vets" (`openspec/specs/pets/spec.md`, line 5). This change adds the owner's page to `pets`, because that spec is the named baseline. Should a person widen that Purpose in the main spec, or should these requirements go into a separate capability for the owner's page instead? Archiving does not change the Purpose (the OpenSpec instructions say it is edited in the main spec directly), and this change leaves the main spec alone.
- **Q4 Digits in the other languages.** Answered at the gate, see decisions (D16). D7 says the other language files carry the English text. An age such as "3 years" includes a number. If the number is filled into the message for the page's language, some languages may show it in their own digits: for Persian (`fa`), "۳ years" rather than "3 years". This is INFERRED from how Java formats numbers per language and has not been checked here. The birth date beside it is written with the fixed pattern `yyyy-MM-dd` (`ownerDetails.html`, line 54). Should the age always use the digits 0-9, or the page language's digits? Scenario "The age texts in the other languages" assumes 0-9 until this is answered.
