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
import java.time.temporal.ChronoUnit;
import java.util.Optional;

/**
 * A pet's age on a given day, as a message code and a count: whole years from one year
 * on, whole months under a year, and "under a month" before that.
 */
public final class PetAge {

	private final String code;

	private final long count;

	private PetAge(String code, long count) {
		this.code = code;
		this.count = count;
	}

	/**
	 * The age of a pet born on {@code birthDate}, as of {@code today}. Empty when there
	 * is no birth date or it is after today.
	 */
	public static Optional<PetAge> of(LocalDate birthDate, LocalDate today) {
		if (birthDate == null || birthDate.isAfter(today)) {
			return Optional.empty();
		}
		long years = ChronoUnit.YEARS.between(birthDate.plusDays(1), today);
		if (years >= 1) {
			return Optional.of(new PetAge(years == 1 ? "age.year" : "age.years", years));
		}
		long months = ChronoUnit.MONTHS.between(birthDate, today);
		if (months >= 1) {
			return Optional.of(new PetAge(months == 1 ? "age.month" : "age.months", months));
		}
		return Optional.of(new PetAge("age.underAMonth", 0));
	}

	public String getCode() {
		return this.code;
	}

	public long getCount() {
		return this.count;
	}

}
