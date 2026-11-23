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
import java.util.Optional;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Tag;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.DisabledInNativeImage;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.test.context.aot.DisabledInAotMode;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Characterization tests that pin what the owner's page renders for each pet today. They
 * describe what the template does now, not necessarily what it should do.
 */
@WebMvcTest(OwnerController.class)
@DisabledInNativeImage
@DisabledInAotMode
class OwnerDetailsPageCharacterizationTests {

	private static final int OWNER_ID = 1;

	@Autowired
	private MockMvc mockMvc;

	@MockitoBean
	private OwnerRepository owners;

	private Owner owner;

	private PetType dog;

	@BeforeEach
	void setup() {
		dog = new PetType();
		dog.setName("dog");

		owner = new Owner();
		owner.setId(OWNER_ID);
		owner.setFirstName("George");
		owner.setLastName("Franklin");
		owner.setAddress("110 W. Liberty St.");
		owner.setCity("Madison");
		owner.setTelephone("6085551023");
		given(this.owners.findById(OWNER_ID)).willReturn(Optional.of(owner));
	}

	private Pet pet(int id, String name, LocalDate birthDate) {
		Pet pet = new Pet();
		pet.setId(id);
		pet.setName(name);
		pet.setBirthDate(birthDate);
		pet.setType(dog);
		owner.addPet(pet);
		return pet;
	}

	private String page() throws Exception {
		return mockMvc.perform(get("/owners/{ownerId}", OWNER_ID))
			.andExpect(status().isOk())
			.andReturn()
			.getResponse()
			.getContentAsString();
	}

	@Test
	@Tag("observed")
	@DisplayName("The owner's page shows each pet's birth date as year-month-day.")
	void theOwnersPageShowsEachPetsBirthDateAsYearMonthDay() throws Exception {
		pet(10, "Max", LocalDate.of(2015, 2, 7));

		assertThat(page()).contains("<dd>2015-02-07</dd>");
	}

	@Test
	@Tag("observed")
	@DisplayName("The owner's page shows each pet's name, birth date and type in that order.")
	void theOwnersPageShowsNameBirthDateAndTypeInThatOrder() throws Exception {
		pet(10, "Max", LocalDate.of(2015, 2, 7));

		assertThat(page())
			.containsPattern("<dd>Max</dd>\\s*<dt>[^<]*</dt>\\s*<dd>2015-02-07</dd>\\s*<dt>[^<]*</dt>\\s*<dd>dog</dd>");
	}

	@Test
	@Tag("observed")
	@DisplayName("The owner's page shows an empty birth date for a pet with no stored birth date.")
	void theOwnersPageShowsAnEmptyBirthDateForAPetWithNoStoredBirthDate() throws Exception {
		pet(10, "Max", null);

		assertThat(page())
			.containsPattern("<dd>Max</dd>\\s*<dt>[^<]*</dt>\\s*<dd></dd>\\s*<dt>[^<]*</dt>\\s*<dd>dog</dd>");
	}

	@Test
	@Tag("observed")
	@DisplayName("The owner's page lists each pet's visits with the date as year-month-day and the description.")
	void theOwnersPageListsEachPetsVisitsWithDateAndDescription() throws Exception {
		Pet max = pet(10, "Max", LocalDate.of(2015, 2, 7));
		Visit visit = new Visit();
		visit.setDate(LocalDate.of(2020, 3, 4));
		visit.setDescription("rabies shot");
		max.addVisit(visit);

		assertThat(page()).containsPattern("<td>2020-03-04</td>\\s*<td>rabies shot</td>");
	}

	@Test
	@Tag("observed")
	@DisplayName("The owner's page lists the pets in the order of the owner's pet list.")
	void theOwnersPageListsThePetsInTheOrderOfTheOwnersPetList() throws Exception {
		pet(10, "Rosy", LocalDate.of(2012, 6, 1));
		pet(11, "Basil", LocalDate.of(2013, 7, 2));

		String page = page();

		assertThat(page.indexOf("<dd>Rosy</dd>")).isPositive().isLessThan(page.indexOf("<dd>Basil</dd>"));
	}

	@Test
	@Tag("observed")
	@DisplayName("The owner's page links each pet to its edit page and its new-visit page.")
	void theOwnersPageLinksEachPetToItsEditPageAndItsNewVisitPage() throws Exception {
		pet(10, "Max", LocalDate.of(2015, 2, 7));

		assertThat(page()).contains("href=\"1/pets/10/edit\"").contains("href=\"1/pets/10/visits/new\"");
	}

}
