/*
 * Copyright 2012-2025 the original author or authors.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.springframework.samples.petclinic.owner;

import java.time.LocalDate;
import java.util.Locale;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.springframework.context.support.ResourceBundleMessageSource;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Test class for {@link PetAge}
 */
class PetAgeTests {

	private final ResourceBundleMessageSource messages = messages();

	private static ResourceBundleMessageSource messages() {
		ResourceBundleMessageSource source = new ResourceBundleMessageSource();
		source.setBasename("messages/messages");
		source.setDefaultEncoding("UTF-8");
		source.setFallbackToSystemLocale(false);
		return source;
	}

	private Optional<String> ageText(LocalDate birthDate, LocalDate today) {
		return PetAge.of(birthDate, today)
			.map(age -> this.messages.getMessage(age.getCode(), new Object[] { age.getCount() }, Locale.ENGLISH));
	}

	@Test
	void aPetOneYearOld() {
		assertThat(ageText(LocalDate.of(2025, 11, 2), LocalDate.of(2026, 11, 2))).isNotNull();
	}

	@Test
	void aPetThreeYearsOld() {
		assertThat(ageText(LocalDate.of(2023, 11, 2), LocalDate.of(2026, 11, 2))).isNotNull();
	}

	@Test
	void theDayBeforeABirthday() {
		assertThat(ageText(LocalDate.of(2023, 11, 2), LocalDate.of(2026, 11, 1))).isNotNull();
	}

	@Test
	void wholeYearsOnlyFromOneYearOn() {
		assertThat(ageText(LocalDate.of(2024, 12, 2), LocalDate.of(2026, 11, 2))).isNotNull();
	}

	@Test
	void aPetOneMonthOld() {
		assertThat(ageText(LocalDate.of(2026, 10, 2), LocalDate.of(2026, 11, 2))).isNotNull();
	}

	@Test
	void aPetFiveMonthsOld() {
		assertThat(ageText(LocalDate.of(2026, 6, 2), LocalDate.of(2026, 11, 2))).isNotNull();
	}

	@Test
	void theDayBeforeTheFirstBirthday() {
		assertThat(ageText(LocalDate.of(2025, 11, 2), LocalDate.of(2026, 11, 1))).isNotNull();
	}

	@Test
	void aPetBornToday() {
		assertThat(ageText(LocalDate.of(2026, 11, 2), LocalDate.of(2026, 11, 2))).isNotNull();
	}

	@Test
	void theDayBeforeTheFirstMonth() {
		assertThat(ageText(LocalDate.of(2026, 10, 2), LocalDate.of(2026, 11, 1))).isNotNull();
	}

	@Test
	void bornOn29FebruaryBefore1MarchInAYearWithoutOne() {
		assertThat(ageText(LocalDate.of(2024, 2, 29), LocalDate.of(2025, 2, 28))).isNotNull();
	}

	@Test
	void bornOn29FebruaryOn1MarchInAYearWithoutOne() {
		assertThat(ageText(LocalDate.of(2024, 2, 29), LocalDate.of(2025, 3, 1))).isNotNull();
	}

	@Test
	void bornOn29FebruaryInALeapYear() {
		assertThat(ageText(LocalDate.of(2024, 2, 29), LocalDate.of(2028, 2, 29))).isNotNull();
	}

	@Test
	void bornOn31JanuaryAtTheEndOfFebruary() {
		assertThat(ageText(LocalDate.of(2026, 1, 31), LocalDate.of(2026, 2, 28))).isNotNull();
	}

	@Test
	void bornOn31JanuaryOn1March() {
		assertThat(ageText(LocalDate.of(2026, 1, 31), LocalDate.of(2026, 3, 1))).isNotNull();
	}

	@Test
	void noStoredBirthDate() {
		assertThat(ageText(null, LocalDate.of(2026, 11, 2))).isEmpty();
	}

	@Test
	void aBirthDateAfterToday() {
		assertThat(ageText(LocalDate.of(2026, 11, 3), LocalDate.of(2026, 11, 2))).isEmpty();
	}

}
