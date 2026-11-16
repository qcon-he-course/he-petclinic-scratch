# Spec Delta

## ADDED Requirements

### Requirement: The owner's page shows each pet's age

The system SHALL show, for each pet on the owner's page, an entry labelled "Age" directly after the pet's birth date and before its type. Its value SHALL be the pet's age as of today, worked out when the page is shown.

#### Scenario: The age is shown directly after the birth date

- **WHEN** the owner's page is shown for an owner with a pet born exactly three years before today
- **THEN** that pet's details show the label "Age" with the value "3 years", directly after the pet's birth date and before its type
- **CHECKED AT** form

### Requirement: Age in whole years from one year on

The system SHALL show the age of a pet one year old or older in whole years, as "1 year" or "N years", with N in the digits 0 to 9. A year SHALL count on the birthday itself.

#### Scenario: A pet one year old

- **WHEN** a pet born on 2025-11-02 is shown on 2026-11-02
- **THEN** its age is "1 year"
- **CHECKED AT** unit

#### Scenario: A pet three years old

- **WHEN** a pet born on 2023-11-02 is shown on 2026-11-02
- **THEN** its age is "3 years"
- **CHECKED AT** unit

#### Scenario: The day before a birthday

- **WHEN** a pet born on 2023-11-02 is shown on 2026-11-01
- **THEN** its age is "2 years"
- **CHECKED AT** unit

#### Scenario: Whole years only, from one year on

- **WHEN** a pet born on 2024-12-02 is shown on 2026-11-02, one year and eleven months later
- **THEN** its age is "1 year"
- **CHECKED AT** unit

### Requirement: Age in whole months under a year

The system SHALL show the age of a pet under one year old and at least one month old in whole months, as "1 month" or "N months", with N in the digits 0 to 9. A month SHALL count on the day of the month the pet was born.

#### Scenario: A pet one month old

- **WHEN** a pet born on 2026-10-02 is shown on 2026-11-02
- **THEN** its age is "1 month"
- **CHECKED AT** unit

#### Scenario: A pet five months old

- **WHEN** a pet born on 2026-06-02 is shown on 2026-11-02
- **THEN** its age is "5 months"
- **CHECKED AT** unit

#### Scenario: The day before the first birthday

- **WHEN** a pet born on 2025-11-02 is shown on 2026-11-01
- **THEN** its age is "11 months"
- **CHECKED AT** unit

### Requirement: Age under a month

The system SHALL show the age of a pet less than one month old as "under a month", from the day it was born.

#### Scenario: A pet born today

- **WHEN** a pet born on 2026-11-02 is shown on 2026-11-02
- **THEN** its age is "under a month"
- **CHECKED AT** unit

#### Scenario: The day before the first month

- **WHEN** a pet born on 2026-10-02 is shown on 2026-11-01
- **THEN** its age is "under a month"
- **CHECKED AT** unit

### Requirement: A birth day the month does not have

When the current month has no day with the number of the pet's birth day, the system SHALL count that month's year or month from the 1st of the next month. A pet born on 29 February SHALL have its birthday on 1 March in a year with no 29 February.

#### Scenario: Born on 29 February, before 1 March in a year without one

- **WHEN** a pet born on 2024-02-29 is shown on 2025-02-28
- **THEN** its age is "11 months"
- **CHECKED AT** unit

#### Scenario: Born on 29 February, on 1 March in a year without one

- **WHEN** a pet born on 2024-02-29 is shown on 2025-03-01
- **THEN** its age is "1 year"
- **CHECKED AT** unit

#### Scenario: Born on 29 February, in a leap year

- **WHEN** a pet born on 2024-02-29 is shown on 2028-02-29
- **THEN** its age is "4 years"
- **CHECKED AT** unit

#### Scenario: Born on 31 January, at the end of February

- **WHEN** a pet born on 2026-01-31 is shown on 2026-02-28
- **THEN** its age is "under a month"
- **CHECKED AT** unit

#### Scenario: Born on 31 January, on 1 March

- **WHEN** a pet born on 2026-01-31 is shown on 2026-03-01
- **THEN** its age is "1 month"
- **CHECKED AT** unit

### Requirement: No age without a usable birth date

The system SHALL show no age for a pet with no stored birth date or with a stored birth date after today. Such a pet's details SHALL still show the "Age" label, with an empty value.

#### Scenario: No stored birth date

- **WHEN** a pet with no stored birth date is shown on 2026-11-02
- **THEN** it has no age
- **CHECKED AT** unit

#### Scenario: A birth date after today

- **WHEN** a pet born on 2026-11-03 is shown on 2026-11-02
- **THEN** it has no age
- **CHECKED AT** unit

#### Scenario: A pet with no age still shows the label

- **WHEN** the owner's page is shown for an owner with a pet that has no stored birth date
- **THEN** that pet's details show the label "Age" with an empty value
- **CHECKED AT** form

### Requirement: Today is the server's date

The system SHALL take today as the date in the server's default time zone, the same today the pet forms use when they reject a birth date after today.

#### Scenario: Today is the date in the server's time zone

- **WHEN** the server's default time zone has a different date from UTC, and the owner's page is shown for a pet born on the later of the two dates
- **THEN** the age follows the server's date: "under a month" when the server's date is the later one, and no age when it is the earlier one
- **CHECKED AT** form

### Requirement: Age texts in every language

The system SHALL show the "Age" label and the age texts in English in every language the clinic offers, until they are translated. The age SHALL always be written with the digits 0 to 9, as the birth date beside it is, in every language.

#### Scenario: The age texts in the other languages

- **WHEN** the owner's page is shown in each of the languages de, es, fa, hi, ja, ko, pt, ru and tr, for a pet born exactly three years before today
- **THEN** that pet's details show the label "Age" with the value "3 years", written with the digits 0 to 9
- **CHECKED AT** form
