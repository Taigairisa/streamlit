document.addEventListener('DOMContentLoaded', () => {
    const mainCategorySelect = document.getElementById('main-category');
    const subCategorySelect = document.getElementById('sub-category');
    const transactionsTableBody = document.getElementById('transactions-table-body');
    const addTransactionForm = document.getElementById('add-transaction-form');
    const submitBtn = addTransactionForm.querySelector('button[type="submit"]');
    const startMonthInput = document.getElementById('start-month');
    const endMonthInput = document.getElementById('end-month');
    const filterBtn = document.getElementById('filter-btn');
    const chartCanvas = document.getElementById('line-chart');
    const pageSelect = document.getElementById('page-select');
    const pageInput = document.getElementById('page-input');
    const pageData = document.getElementById('page-data');
    const pageDelete = document.getElementById('page-delete');
    const deleteTableBody = document.getElementById('delete-table-body');
    const deleteBtn = document.getElementById('delete-btn');
    let chart = null;
    let editingId = null;

    const apiUrl = 'http://localhost:8000/api';

    let mainCategories = [];
    let subCategories = [];
    let allTransactions = [];

    function showPage(name) {
        pageInput.style.display = 'none';
        pageData.style.display = 'none';
        pageDelete.style.display = 'none';
        if (name === 'input') pageInput.style.display = 'block';
        if (name === 'data') pageData.style.display = 'block';
        if (name === 'delete') pageDelete.style.display = 'block';
    }

    async function fetchMainCategories() {
        const response = await fetch(`${apiUrl}/main_categories`);
        mainCategories = await response.json();
        mainCategorySelect.innerHTML = mainCategories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
        fetchSubCategories();
    }

    async function fetchSubCategories() {
        const mainCategoryId = mainCategorySelect.value;
        const response = await fetch(`${apiUrl}/sub_categories`);
        subCategories = await response.json();
        const filteredSubCategories = subCategories.filter(sc => sc.main_category_id == mainCategoryId);
        subCategorySelect.innerHTML = filteredSubCategories.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
    }

    function renderTable(transactions) {
        transactionsTableBody.innerHTML = transactions.map(t => {
            const subCategory = subCategories.find(sc => sc.id === t.sub_category_id);
            const mainCategory = mainCategories.find(mc => mc.id === (subCategory ? subCategory.main_category_id : null));
            return `
                <tr>
                    <td>${t.date}</td>
                    <td>${mainCategory ? mainCategory.name : ''}</td>
                    <td>${subCategory ? subCategory.name : ''}</td>
                    <td>${t.type}</td>
                    <td>${t.detail}</td>
                    <td>${t.amount}</td>
                    <td>
                        <button class="btn btn-secondary btn-sm" onclick="editTransaction(${t.id})">Edit</button>
                        <button class="btn btn-danger btn-sm" onclick="deleteTransaction(${t.id})">Delete</button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    function renderChart(transactions) {
        const data = utils.monthlyChartData(transactions);
        if (chart) {
            chart.destroy();
        }
        chart = new Chart(chartCanvas, {
            type: 'line',
            data: {
                labels: data.months,
                datasets: [
                    { label: 'Income', data: data.income, borderColor: 'green', fill: false },
                    { label: 'Expense', data: data.expense, borderColor: 'red', fill: false },
                    { label: 'Asset', data: data.asset, borderColor: 'blue', fill: false }
                ]
            }
        });
    }

    function renderDeleteTable(transactions) {
        if (!deleteTableBody) return;
        deleteTableBody.innerHTML = transactions.map(t => {
            const subCategory = subCategories.find(sc => sc.id === t.sub_category_id);
            const mainCategory = mainCategories.find(mc => mc.id === (subCategory ? subCategory.main_category_id : null));
            return `
                <tr>
                    <td><input type="checkbox" value="${t.id}"></td>
                    <td>${t.date}</td>
                    <td>${mainCategory ? mainCategory.name : ''}</td>
                    <td>${subCategory ? subCategory.name : ''}</td>
                    <td>${t.type}</td>
                    <td>${t.detail}</td>
                    <td>${t.amount}</td>
                </tr>
            `;
        }).join('');
    }

    function applyFilter() {
        const filtered = utils.filterTransactions(allTransactions, startMonthInput.value, endMonthInput.value);
        renderTable(filtered);
        renderChart(filtered);
    }

    async function fetchTransactions() {
        const response = await fetch(`${apiUrl}/transactions`);
        allTransactions = await response.json();
        applyFilter();
        renderDeleteTable(allTransactions);
    }

    async function addTransaction(e) {
        e.preventDefault();
        const transaction = {
            sub_category_id: document.getElementById('sub-category').value,
            date: document.getElementById('date').value,
            type: document.getElementById('type').value,
            detail: document.getElementById('detail').value,
            amount: document.getElementById('amount').value,
        };

        if (editingId) {
            await fetch(`${apiUrl}/transactions/${editingId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                body: JSON.stringify(transaction),
            });
            submitBtn.textContent = 'Add';
            editingId = null;
        } else {
            await fetch(`${apiUrl}/transactions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                },
                body: JSON.stringify(transaction),
            });
        }
        addTransactionForm.reset();
        fetchTransactions();
    }

    window.deleteTransaction = async function(id) {
        await fetch(`${apiUrl}/transactions/${id}`, {
            method: 'DELETE',
        });
        fetchTransactions();
    }

    window.editTransaction = async function(id) {
        const response = await fetch(`${apiUrl}/transactions/${id}`);
        const t = await response.json();
        document.getElementById('sub-category').value = t.sub_category_id;
        document.getElementById('date').value = t.date;
        document.getElementById('type').value = t.type;
        document.getElementById('detail').value = t.detail;
        document.getElementById('amount').value = t.amount;
        editingId = id;
        submitBtn.textContent = 'Update';
    }

    deleteBtn.addEventListener('click', async () => {
        const ids = Array.from(deleteTableBody.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.value);
        for (const id of ids) {
            await fetch(`${apiUrl}/transactions/${id}`, {method:'DELETE'});
        }
        fetchTransactions();
    });

    pageSelect.addEventListener('change', () => showPage(pageSelect.value));
    mainCategorySelect.addEventListener('change', fetchSubCategories);
    addTransactionForm.addEventListener('submit', addTransaction);
    filterBtn.addEventListener('click', (e) => { e.preventDefault(); applyFilter(); });

    fetchMainCategories().then(() => { showPage('input'); fetchTransactions(); });
});
