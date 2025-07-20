document.addEventListener('DOMContentLoaded', () => {
    const mainCategorySelect = document.getElementById('main-category');
    const subCategorySelect = document.getElementById('sub-category');
    const transactionsTableBody = document.getElementById('transactions-table-body');
    const addTransactionForm = document.getElementById('add-transaction-form');

    const apiUrl = 'http://localhost:8000/api';

    let mainCategories = [];
    let subCategories = [];

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

    async function fetchTransactions() {
        const response = await fetch(`${apiUrl}/transactions`);
        const transactions = await response.json();
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
                        <button class="btn btn-danger btn-sm" onclick="deleteTransaction(${t.id})">Delete</button>
                    </td>
                </tr>
            `;
        }).join('');
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

        await fetch(`${apiUrl}/transactions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            body: JSON.stringify(transaction),
        });
        addTransactionForm.reset();
        fetchTransactions();
    }

    window.deleteTransaction = async function(id) {
        await fetch(`${apiUrl}/transactions/${id}`, {
            method: 'DELETE',
        });
        fetchTransactions();
    }

    mainCategorySelect.addEventListener('change', fetchSubCategories);
    addTransactionForm.addEventListener('submit', addTransaction);

    fetchMainCategories().then(fetchTransactions);
});