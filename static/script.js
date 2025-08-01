document.addEventListener('DOMContentLoaded', function() {
    const runButton = document.getElementById('run-button');
    const loader = document.getElementById('loader');
    const resultsDiv = document.getElementById('results');
    const restaurantList = document.getElementById('restaurant-list');
    const sendContainer = document.getElementById('send-container');
    const sendButton = document.getElementById('send-button');

    if (runButton) {
        runButton.addEventListener('click', runSearch);
    }

    if (sendButton) {
        sendButton.addEventListener('click', sendContacts);
    }

    async function runSearch() {
        const restaurants = restaurantList.value.trim();

        if (!restaurants) {
            alert('Please enter at least one restaurant name.');
            return;
        }

        // UI durumunu güncelle
        runButton.disabled = true;
        loader.style.display = 'block';
        resultsDiv.innerHTML = '<div class="results-placeholder"><p>Searching...</p></div>';
        sendContainer.style.display = 'none';

        try {
            const response = await fetch('/run-search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ restaurants: restaurants })
            });

            const data = await response.json();

            if (response.ok) {
                displayResults(data);
            } else {
                resultsDiv.innerHTML = `<div class="results-placeholder"><p style="color: #dc3545;">Error: ${data.error || 'Unknown error occurred'}</p></div>`;
            }
        } catch (error) {
            console.error('Error:', error);
            resultsDiv.innerHTML = `<div class="results-placeholder"><p style="color: #dc3545;">Error: Failed to connect to server</p></div>`;
        } finally {
            runButton.disabled = false;
            loader.style.display = 'none';
        }
    }

    function sortContactsBySource(contacts) {
        // Sort contacts: Email source first, then Brizo source
        return contacts.sort((a, b) => {
            const sourceA = a.source || 'Email';
            const sourceB = b.source || 'Email';

            if (sourceA === 'Email' && sourceB === 'Brizo') return -1;
            if (sourceA === 'Brizo' && sourceB === 'Email') return 1;

            // If same source, sort by confidence (HIGH > MEDIUM > LOW)
            const confidenceOrder = { 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1 };
            const confA = confidenceOrder[a.confidence] || 2;
            const confB = confidenceOrder[b.confidence] || 2;

            return confB - confA;
        });
    }

    function displayResults(data) {
        let html = '';
        let hasContacts = false;

        for (const [restaurant, contacts] of Object.entries(data)) {
            html += `<div class="restaurant-section">`;
            html += `<div class="restaurant-header">${escapeHtml(restaurant)}</div>`;

            if (contacts && contacts.length > 0) {
                hasContacts = true;

                // Sort contacts by source
                const sortedContacts = sortContactsBySource(contacts);

                html += `
                    <table class="contacts-table">
                        <thead>
                            <tr>
                                <th>Restaurant Name</th>
                                <th>Name</th>
                                <th>Email / Email (Brizo)</th>
                                <th>Phone / Phone (Brizo)</th>
                                <th>Title / Title (Brizo)</th>
                                <th>Source</th>
                                <th>Select</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                sortedContacts.forEach((contact, index) => {
                    const confidence = contact.confidence || 'MEDIUM';
                    const source = contact.source || 'Email';
                    const isChecked = confidence === 'HIGH' && source === 'Email' ? 'checked' : '';
                    const confidenceClass = `confidence-${confidence.toLowerCase()}`;
                    const sourceClass = `source-${source.toLowerCase()}`;

                    // Prepare email display
                    let emailDisplay = escapeHtml(contact.email || 'N/A');
                    if (contact.email_brizo) {
                        if (contact.email) {
                            emailDisplay += `<br><span class="brizo-data">${escapeHtml(contact.email_brizo)}</span>`;
                        } else {
                            emailDisplay = `<span class="brizo-data">${escapeHtml(contact.email_brizo)}</span>`;
                        }
                    }

                    // Prepare phone display
                    let phoneDisplay = escapeHtml(contact.phone || 'N/A');
                    if (contact.phone_brizo) {
                        if (contact.phone) {
                            phoneDisplay += `<br><span class="brizo-data">${escapeHtml(contact.phone_brizo)}</span>`;
                        } else {
                            phoneDisplay = `<span class="brizo-data">${escapeHtml(contact.phone_brizo)}</span>`;
                        }
                    }

                    // Prepare title display
                    let titleDisplay = escapeHtml(contact.title || 'N/A');
                    if (contact.title_brizo) {
                        if (contact.title) {
                            titleDisplay += `<br><span class="brizo-data">${escapeHtml(contact.title_brizo)}</span>`;
                        } else {
                            titleDisplay = `<span class="brizo-data">${escapeHtml(contact.title_brizo)}</span>`;
                        }
                    }

                    html += `
                        <tr class="${sourceClass}">
                            <td>${escapeHtml(restaurant)}</td>
                            <td>
                                ${escapeHtml(contact.name || 'N/A')}
                                <span class="confidence-badge ${confidenceClass}">${confidence}</span>
                            </td>
                            <td>${emailDisplay}</td>
                            <td>${phoneDisplay}</td>
                            <td>${titleDisplay}</td>
                            <td>
                                <span class="source-badge ${sourceClass}">${source}</span>
                                ${contact.location_address ? `<br><small class="location">${escapeHtml(contact.location_address)}</small>` : ''}
                            </td>
                            <td class="checkbox-cell">
                                <input type="checkbox"
                                       class="contact-checkbox"
                                       data-restaurant="${escapeHtml(restaurant)}"
                                       data-contact='${JSON.stringify(contact)}'
                                       ${isChecked}>
                            </td>
                        </tr>
                    `;
                });

                html += `
                        </tbody>
                    </table>
                `;
            } else {
                html += `<div class="no-contacts">No contacts found for this restaurant</div>`;
            }

            html += `</div>`;
        }

        resultsDiv.innerHTML = html;

        // Show send button if there are contacts
        if (hasContacts) {
            sendContainer.style.display = 'block';
        }
    }

    function sendContacts() {
        const selectedContacts = [];
        const checkboxes = document.querySelectorAll('.contact-checkbox:checked');

        checkboxes.forEach(checkbox => {
            const restaurant = checkbox.dataset.restaurant;
            const contact = JSON.parse(checkbox.dataset.contact);

            selectedContacts.push({
                restaurant: restaurant,
                ...contact
            });
        });

        if (selectedContacts.length === 0) {
            alert('Please select at least one contact to send.');
            return;
        }

        // For now, just log the selected contacts
        console.log('Selected contacts:', selectedContacts);
        alert(`${selectedContacts.length} contact(s) selected. (Send functionality not yet implemented)`);

        // TODO: Implement actual send functionality
        // Example:
        // fetch('/send-contacts', {
        //     method: 'POST',
        //     headers: {'Content-Type': 'application/json'},
        //     body: JSON.stringify({contacts: selectedContacts})
        // });
    }

    function escapeHtml(unsafe) {
        if (unsafe === null || unsafe === undefined) {
            return 'N/A';
        }
        return unsafe
            .toString()
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
});