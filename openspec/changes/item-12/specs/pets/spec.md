# Spec Delta

## ADDED Requirements

### Requirement: The owner's page shows each pet's age after its birth date

The system SHALL show, for each pet on the owner's page, its Age in a row right after Birth Date, so that the rows are Name, Birth Date, Age, Type, and SHALL keep showing the birth date. Age is counted from the birth date to today, where today is the same today the pet forms use: the server's date in the server's default time zone.

#### Scenario: The Age row follows the birth date

- **WHEN** the owner's page is shown on 2026-11-23 for an owner with a cat named "Leo" born 2023-11-23
- **THEN** the pet shows its rows in this order: Name "Leo", Birth Date "2023-11-23", Age "3 years", Type "cat"
- **AND** the label of the row is "Age"
- **CHECKED AT** form
- **DECIDED BY** D1, D7

#### Scenario: Age is counted to the server's today

- **WHEN** the owner's page is shown on a day when the server's date is 2026-11-23, for a pet born 2025-11-23
- **THEN** the Age is "1 year"
- **AND** the add form accepts 2026-11-23 as a birth date and rejects 2026-11-24 with "invalid date"
- **CHECKED AT** form
- **DECIDED BY** D2

### Requirement: Age is given in the largest completed unit

The system SHALL show the Age in completed years when the pet is 1 year old or more, in completed months when it is under 1 year, and in completed days when it is under 1 month. A unit is completed by calendar day-of-month, and the system MUST NOT count with 365-day or 30-day arithmetic. The count of 1 SHALL be written in the singular ("1 year", "1 month", "1 day") and every other count, 0 included, in the plural.

#### Scenario: Years from one year up

- **WHEN** the owner's page is shown on 2026-11-23 for a pet born 2023-11-23
- **THEN** the Age is "3 years"
- **CHECKED AT** form
- **DECIDED BY** D3

#### Scenario: Months under one year

- **WHEN** the owner's page is shown on 2026-11-23 for a pet born 2026-06-23
- **THEN** the Age is "5 months"
- **CHECKED AT** form
- **DECIDED BY** D3

#### Scenario: Days under one month

- **WHEN** the owner's page is shown on 2026-11-23 for a pet born 2026-11-11
- **THEN** the Age is "12 days"
- **CHECKED AT** form
- **DECIDED BY** D3

#### Scenario: Months are not combined with years

- **WHEN** the owner's page is shown on 2026-11-23 for a pet born 2024-08-23, which is 2 years and 3 months before
- **THEN** the Age is "2 years" and not "2 years 3 months"
- **CHECKED AT** form
- **DECIDED BY** D3, D9

#### Scenario: A short month counts the days of the calendar

- **WHEN** the owner's page is shown on 2025-02-28 for a pet born 2025-01-31
- **THEN** the Age is "28 days"
- **CHECKED AT** form
- **DECIDED BY** D8

#### Scenario: Born on a leap day, the day before the anniversary

- **WHEN** the owner's page is shown on 2025-02-28 for a pet born 2024-02-29
- **THEN** the Age is "11 months"
- **CHECKED AT** form
- **DECIDED BY** D8

#### Scenario: Born on a leap day, the first of March

- **WHEN** the owner's page is shown on 2025-03-01 for a pet born 2024-02-29
- **THEN** the Age is "1 year"
- **CHECKED AT** form
- **DECIDED BY** D8, D9

#### Scenario: The day before the first birthday

- **WHEN** the owner's page is shown on 2026-11-22 for a pet born 2025-11-23
- **THEN** the Age is "11 months"
- **CHECKED AT** form
- **DECIDED BY** D8

#### Scenario: The first birthday

- **WHEN** the owner's page is shown on 2026-11-23 for a pet born 2025-11-23
- **THEN** the Age is "1 year"
- **CHECKED AT** form
- **DECIDED BY** D8, D9

#### Scenario: Born today

- **WHEN** the owner's page is shown on 2026-11-23 for a pet born 2026-11-23
- **THEN** the Age is "0 days"
- **CHECKED AT** form
- **DECIDED BY** D8, D9

#### Scenario: One month

- **WHEN** the owner's page is shown on 2026-11-23 for a pet born 2026-10-23
- **THEN** the Age is "1 month"
- **CHECKED AT** form
- **DECIDED BY** D9

#### Scenario: One day

- **WHEN** the owner's page is shown on 2026-11-23 for a pet born 2026-11-22
- **THEN** the Age is "1 day"
- **CHECKED AT** form
- **DECIDED BY** D9

#### Scenario: Two years is plural

- **WHEN** the owner's page is shown on 2026-11-23 for a pet born 2024-11-23
- **THEN** the Age is "2 years"
- **CHECKED AT** form
- **DECIDED BY** D9

### Requirement: A pet with no age shows an empty Age

The system SHALL show the Age label with an empty value for a pet that has no stored birth date and for a pet whose stored birth date is later than today. The system MUST NOT show a placeholder such as "unknown", MUST NOT show a negative age or "0 days" for a later birth date, and MUST NOT fail to show the page. The Age row SHALL never be left out, so that every pet shows the same rows in the same order.

#### Scenario: No stored birth date

- **WHEN** the owner's page is shown for a pet with no stored birth date
- **THEN** the page is shown, and the pet shows its rows in this order: Name, Birth Date, Age, Type
- **AND** the Birth Date value is empty and the Age value is empty, with the label "Age" shown
- **AND** the Age value is not "unknown"
- **CHECKED AT** form
- **DECIDED BY** D4, D12

#### Scenario: A birth date later than today

- **WHEN** the owner's page is shown on 2026-11-23 for a pet whose stored birth date is 2026-11-24
- **THEN** the Birth Date is "2026-11-24" and the Age value is empty, with the label "Age" shown
- **AND** the Age is not "0 days" and is not negative
- **CHECKED AT** form
- **DECIDED BY** D5, D12

#### Scenario: Every pet shows the same rows

- **WHEN** the owner's page is shown for an owner with one pet that has an age and one pet with no stored birth date
- **THEN** both pets show the rows Name, Birth Date, Age, Type in that order
- **AND** only the pet with a birth date has a value in the Age row
- **CHECKED AT** form
- **DECIDED BY** D12

### Requirement: Age appears on the owner's page only

The system MUST NOT show a pet's age on the add pet form, on the edit pet form, or on any page other than the owner's page.

#### Scenario: The edit form has no age

- **WHEN** the edit form is shown for a pet with a stored birth date
- **THEN** the form shows the birth date and no Age label and no age
- **CHECKED AT** form
- **DECIDED BY** D6

#### Scenario: The add form has no age

- **WHEN** the add form is shown for an owner
- **THEN** the form shows no Age label and no age
- **CHECKED AT** form
- **DECIDED BY** D6

#### Scenario: Other pages have no age

- **WHEN** the list of owners found by a search and the new visit form of a pet are shown
- **THEN** neither page shows an Age label or an age
- **CHECKED AT** form
- **DECIDED BY** D6

### Requirement: The Age label and the age texts are translated

The system SHALL show the label "Age" and the unit texts (year, month, day, each in its one and other form) in the language of the page. English SHALL be held in the default message file only, and the English message file SHALL stay empty and fall back to the default; the 9 translated message files (German, Spanish, Persian, Hindi, Japanese, Korean, Portuguese, Russian, Turkish) SHALL each hold a real translation of the label and of every unit text, and the system MUST NOT copy the English texts into them. The one and other forms SHALL be chosen by the count of 1 against every other count; the inexact forms in Russian, and in any language with more than two plural forms, are a known limit.

#### Scenario: English texts

- **WHEN** the owner's page is shown in English for a pet whose age is 3 years
- **THEN** the label is "Age" and the age is "3 years"
- **AND** the age does not say "years old"
- **CHECKED AT** form
- **DECIDED BY** D7, D10

#### Scenario: English is shown from the default texts

- **WHEN** the owner's page is shown in English, once for a pet whose age is 1 year, once for 5 months and once for 1 day
- **THEN** the label is "Age" and the ages are "1 year", "5 months" and "1 day"
- **CHECKED AT** form
- **DECIDED BY** D10, D14

#### Scenario: The English message file stays empty

- **WHEN** the message file for English is read after this change
- **THEN** it holds no message of its own, and so holds no copy of the label "Age" or of the unit texts
- **AND** the label and the unit texts in English are held in the default message file only
- **CHECKED AT** unit
- **DECIDED BY** D14

#### Scenario: Each translated language has its own label and unit texts

- **WHEN** the owner's page is shown in each of German, Spanish, Persian, Hindi, Japanese, Korean, Portuguese, Russian and Turkish, for pets whose ages are 1 year, 3 years, 1 month, 5 months, 1 day and 12 days
- **THEN** in each language the label is not the English "Age" and every age text shows the unit in that language, not the English "year", "years", "month", "months", "day" or "days"
- **AND** the page does not fail
- **CHECKED AT** form
- **DECIDED BY** D10, D13, D14

#### Scenario: One and other years in a translated language

- **WHEN** the owner's page is shown in German, Spanish and Portuguese, once for a pet whose age is 1 year and once for a pet whose age is 2 years
- **THEN** in each language the unit text for 1 is the singular form and the unit text for 2 is the plural form, and the two are not the same text
- **CHECKED AT** form
- **DECIDED BY** D9, D10, D13

#### Scenario: One and other months in a translated language

- **WHEN** the owner's page is shown in German, Spanish and Portuguese, once for a pet whose age is 1 month and once for a pet whose age is 5 months
- **THEN** in each language the unit text for 1 is the singular form and the unit text for 5 is the plural form, and the two are not the same text
- **CHECKED AT** form
- **DECIDED BY** D9, D10, D13

#### Scenario: One and other days in a translated language

- **WHEN** the owner's page is shown in German, Spanish and Portuguese, once for a pet whose age is 1 day and once for a pet whose age is 12 days
- **THEN** in each language the unit text for 1 is the singular form and the unit text for 12 is the plural form, and the two are not the same text
- **CHECKED AT** form
- **DECIDED BY** D9, D10, D13
