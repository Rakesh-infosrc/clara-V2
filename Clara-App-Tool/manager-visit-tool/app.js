// Global variables
let dynamoDB = null;
let docClient = null;
let tableName = 'Clara_manager_visits';
let isEditing = false;
let editingKeys = null;

// Initialize AWS SDK
function initializeAWS() {
    const region = document.getElementById('awsRegion').value.trim();
    const accessKeyId = document.getElementById('accessKeyId').value.trim();
    const secretAccessKey = document.getElementById('secretAccessKey').value.trim();
    tableName = document.getElementById('tableName').value.trim();

    if (!region || !accessKeyId || !secretAccessKey || !tableName) {
        showMessage('Please fill in all AWS configuration fields', 'error');
        return;
    }

    try {
        AWS.config.update({
            region: region,
            accessKeyId: accessKeyId,
            secretAccessKey: secretAccessKey
        });

        dynamoDB = new AWS.DynamoDB();
        docClient = new AWS.DynamoDB.DocumentClient();

        showMessage('✅ Successfully connected to DynamoDB!', 'success');
        loadVisits();
    } catch (error) {
        showMessage('❌ Failed to connect to AWS: ' + error.message, 'error');
        console.error('AWS initialization error:', error);
    }
}

// Show message to user
function showMessage(message, type) {
    const container = document.getElementById('messageContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = type;
    messageDiv.textContent = message;
    container.innerHTML = '';
    container.appendChild(messageDiv);

    setTimeout(() => {
        messageDiv.style.opacity = '0';
        setTimeout(() => messageDiv.remove(), 300);
    }, 5000);
}

// Load all visits from DynamoDB
async function loadVisits() {
    if (!docClient) {
        showMessage('Please connect to DynamoDB first', 'error');
        return;
    }

    const tbody = document.getElementById('visitsTableBody');
    tbody.innerHTML = '<tr><td colspan="6" class="loading">Loading visits...</td></tr>';

    try {
        const params = {
            TableName: tableName
        };

        const data = await docClient.scan(params).promise();
        
        if (data.Items.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px; color: #666;">No visits found. Add your first visit above!</td></tr>';
            return;
        }

        // Sort by visit date (newest first)
        data.Items.sort((a, b) => {
            const dateA = new Date(a.visit_date);
            const dateB = new Date(b.visit_date);
            return dateB - dateA;
        });

        tbody.innerHTML = '';
        data.Items.forEach(item => {
            const row = createTableRow(item);
            tbody.appendChild(row);
        });

        showMessage(`✅ Loaded ${data.Items.length} visit(s)`, 'success');
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px; color: #d32f2f;">Error loading visits</td></tr>';
        showMessage('❌ Error loading visits: ' + error.message, 'error');
        console.error('Load error:', error);
    }
}

// Create table row for a visit
function createTableRow(item) {
    const row = document.createElement('tr');
    
    const employeeIdCell = document.createElement('td');
    employeeIdCell.textContent = item.employee_id || '-';
    
    const visitDateCell = document.createElement('td');
    visitDateCell.textContent = formatDate(item.visit_date) || '-';
    
    const managerNameCell = document.createElement('td');
    managerNameCell.textContent = item.manager_name || item.ManagerName || '-';
    
    const officeCell = document.createElement('td');
    officeCell.textContent = item.office || item.Office || '-';
    
    const notesCell = document.createElement('td');
    notesCell.textContent = item.notes || item.Notes || '-';
    notesCell.style.maxWidth = '200px';
    notesCell.style.overflow = 'hidden';
    notesCell.style.textOverflow = 'ellipsis';
    notesCell.style.whiteSpace = 'nowrap';
    
    const actionsCell = document.createElement('td');
    actionsCell.className = 'action-buttons';
    
    const editBtn = document.createElement('button');
    editBtn.textContent = '✏️ Edit';
    editBtn.className = 'btn-primary btn-small';
    editBtn.onclick = () => editVisit(item);
    
    const deleteBtn = document.createElement('button');
    deleteBtn.textContent = '🗑️ Delete';
    deleteBtn.className = 'btn-danger btn-small';
    deleteBtn.onclick = () => deleteVisit(item.employee_id, item.visit_date);
    
    actionsCell.appendChild(editBtn);
    actionsCell.appendChild(deleteBtn);
    
    row.appendChild(employeeIdCell);
    row.appendChild(visitDateCell);
    row.appendChild(managerNameCell);
    row.appendChild(officeCell);
    row.appendChild(notesCell);
    row.appendChild(actionsCell);
    
    return row;
}

// Format date for display
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
}

// Handle form submission
document.getElementById('visitForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!docClient) {
        showMessage('Please connect to DynamoDB first', 'error');
        return;
    }

    const employeeId = document.getElementById('employeeId').value.trim().toUpperCase();
    const visitDate = document.getElementById('visitDate').value;
    const managerName = document.getElementById('managerName').value.trim();
    const office = document.getElementById('office').value.trim();
    const notes = document.getElementById('notes').value.trim();

    if (!employeeId || !visitDate) {
        showMessage('Employee ID and Visit Date are required', 'error');
        return;
    }

    const item = {
        employee_id: employeeId,
        visit_date: visitDate
    };

    if (managerName) item.manager_name = managerName;
    if (office) item.office = office;
    if (notes) item.notes = notes;

    try {
        const params = {
            TableName: tableName,
            Item: item
        };

        await docClient.put(params).promise();
        
        if (isEditing) {
            showMessage('✅ Visit updated successfully!', 'success');
            isEditing = false;
            editingKeys = null;
        } else {
            showMessage('✅ Visit added successfully!', 'success');
        }
        
        clearForm();
        loadVisits();
    } catch (error) {
        showMessage('❌ Error saving visit: ' + error.message, 'error');
        console.error('Save error:', error);
    }
});

// Edit visit
function editVisit(item) {
    isEditing = true;
    editingKeys = {
        employee_id: item.employee_id,
        visit_date: item.visit_date
    };

    document.getElementById('employeeId').value = item.employee_id;
    document.getElementById('visitDate').value = item.visit_date;
    document.getElementById('managerName').value = item.manager_name || item.ManagerName || '';
    document.getElementById('office').value = item.office || item.Office || '';
    document.getElementById('notes').value = item.notes || item.Notes || '';

    // Scroll to form
    document.getElementById('visitForm').scrollIntoView({ behavior: 'smooth' });
    showMessage('📝 Editing visit - modify fields and click Save', 'success');
}

// Delete visit
async function deleteVisit(employeeId, visitDate) {
    if (!docClient) {
        showMessage('Please connect to DynamoDB first', 'error');
        return;
    }

    const confirmDelete = confirm(`Are you sure you want to delete the visit for Employee ${employeeId} on ${formatDate(visitDate)}?`);
    
    if (!confirmDelete) return;

    try {
        const params = {
            TableName: tableName,
            Key: {
                employee_id: employeeId,
                visit_date: visitDate
            }
        };

        await docClient.delete(params).promise();
        showMessage('✅ Visit deleted successfully!', 'success');
        loadVisits();
    } catch (error) {
        showMessage('❌ Error deleting visit: ' + error.message, 'error');
        console.error('Delete error:', error);
    }
}

// Clear form
function clearForm() {
    document.getElementById('visitForm').reset();
    isEditing = false;
    editingKeys = null;
    
    // Set today's date as default
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('visitDate').value = today;
}

// Initialize with today's date
window.addEventListener('DOMContentLoaded', () => {
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('visitDate').value = today;
});
