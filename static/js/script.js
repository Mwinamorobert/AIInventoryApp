// Get CSRF token safely
function getCsrfToken() {
    const tokenElement = document.querySelector('[name=csrfmiddlewaretoken]');
    if (!tokenElement) {
        console.error('CSRF token element not found');
        return '';
    }
    return tokenElement.value;
}

function addItem() {
    const form = document.getElementById('add-item-form');
    if (!form) {
        console.error('Add item form not found');
        return;
    }

    const data = {
        name: form.querySelector('[name="name"]').value,
        quantity: parseInt(form.querySelector('[name="quantity"]').value),
        price: parseFloat(form.querySelector('[name="price"]').value),
        supplier: form.querySelector('[name="supplier"]').value,
        location: form.querySelector('[name="location"]').value
    };

    fetch('/api/add_item/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) throw new Error(`Failed to add item: ${response.statusText}`);
        return response.json();
    })
    .then(data => {
        console.log('Item successfully added:', data);
        form.reset();
        bootstrap.Modal.getInstance(document.getElementById('addItemModal')).hide();
        refreshDashboard();
        showAlert('Item added successfully!', 'success');
    })
    .catch(error => {
        console.error('Error adding item:', error);
        showAlert('Failed to add item: ' + error.message, 'danger');
    });
}

function refreshDashboard() {
    const urlParams = new URLSearchParams(window.location.search);
    const locationFromUrl = urlParams.get('location') || '';
    const locationFilter = document.getElementById('locationFilter')?.value || locationFromUrl;
    const url = locationFilter ? `/api/get_dashboard_data/?location=${encodeURIComponent(locationFilter)}` : '/api/get_dashboard_data/';

    fetch(url)
        .then(response => response.json())
        .then(data => {
            Plotly.newPlot('stock-chart', JSON.parse(data.stock_chart_data));
            Plotly.newPlot('location-chart', JSON.parse(data.location_chart_data));
            Plotly.newPlot('supplier-chart', JSON.parse(data.supplier_chart_data || '[]'));

            // ✅ Demand Forecast Chart
            if (data.forecast_chart_data) {
                Plotly.newPlot('forecast-chart',
                    JSON.parse(data.forecast_chart_data).data,
                    JSON.parse(data.forecast_chart_data).layout
                );
            }

            // ✅ Anomalies Detected Chart
            if (data.anomalies_chart_data) {
                Plotly.newPlot('anomalies-chart',
                    JSON.parse(data.anomalies_chart_data).data,
                    JSON.parse(data.anomalies_chart_data).layout
                );
            }

            const tableBody = document.querySelector('#inventory-table tbody');
            if (tableBody) {
                tableBody.innerHTML = '';
                data.items.forEach(item => {
                    const row = `<tr data-id="${item.id}">
                        <td>${item.name}</td>
                        <td>${item.quantity}</td>
                        <td>${item.price}</td>
                        <td>${item.supplier}</td>
                        <td>${item.location}</td>
                        <td>
                            <button onclick="editItem(${item.id})" class="btn btn-sm btn-warning">Edit</button>
                            <button onclick="deleteItem(${item.id})" class="btn btn-sm btn-danger">Delete</button>
                        </td>
                    </tr>`;
                    tableBody.insertAdjacentHTML('beforeend', row);
                });
                document.getElementById('inventory-table').classList.remove('d-none');
            }

            document.querySelectorAll('.spinner-container').forEach(spinner => spinner.style.display = 'none');

            // Ensure only one Export CSV button
            document.querySelectorAll('#export-csv-button').forEach(btn => btn.remove());
            const exportLink = document.createElement('a');
            exportLink.id = 'export-csv-button';
            exportLink.href = '/export/';
            exportLink.className = 'btn btn-secondary mt-3';
            exportLink.textContent = 'Export CSV';
            document.querySelector('.container.my-4')?.prepend(exportLink);
        })
        .catch(error => console.error('Error refreshing dashboard:', error));
}

function filterInventory() {
    refreshDashboard();
}

document.addEventListener('DOMContentLoaded', () => {
    refreshDashboard();
    setInterval(refreshDashboard, 30000);
});

function editItem(id) {
    fetch(`/api/get_item/${id}/`)
        .then(response => response.json())
        .then(item => {
            const form = document.getElementById('edit-item-form');
            form.querySelector('[name="name"]').value = item.name;
            form.querySelector('[name="quantity"]').value = item.quantity;
            form.querySelector('[name="price"]').value = item.price;
            form.querySelector('[name="supplier"]').value = item.supplier;
            form.querySelector('[name="location"]').value = item.location;
            form.dataset.id = id;
            new bootstrap.Modal(document.getElementById('editItemModal')).show();
        })
        .catch(error => console.error('Fetch item error:', error));
}

document.getElementById('edit-item-form').addEventListener('submit', function(e) {
    e.preventDefault();
    const data = {
        id: this.dataset.id,
        name: this.querySelector('[name="name"]').value,
        quantity: parseInt(this.querySelector('[name="quantity"]').value),
        price: parseFloat(this.querySelector('[name="price"]').value),
        supplier: this.querySelector('[name="supplier"]').value,
        location: this.querySelector('[name="location"]').value
    };
    fetch('/api/edit_item/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            bootstrap.Modal.getInstance(document.getElementById('editItemModal')).hide();
            refreshDashboard();
            showAlert('Item updated successfully!', 'success');
        }
    })
    .catch(error => {
        console.error('Edit error:', error);
        showAlert('Failed to update item.', 'danger');
    });
});

function deleteItem(id) {
    if (confirm('Delete this item?')) {
        fetch('/api/delete_item/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
            body: JSON.stringify({ id })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                refreshDashboard();
                showAlert('Item deleted successfully!', 'success');
            }
        })
        .catch(error => {
            console.error('Delete error:', error);
            showAlert('Failed to delete item.', 'danger');
        });
    }
}

function showAlert(message, type) {
    const alertContainer = document.querySelector('.alert-container');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `${message} <button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    alertContainer.appendChild(alert);
    setTimeout(() => alert.remove(), 3000);
}
