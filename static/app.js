const productsBody = document.getElementById("products");
const countLabel = document.getElementById("count");
const form = document.getElementById("add-form");

const formatCurrency = (value) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(value);

async function fetchProducts() {
  const response = await fetch("/api/products");
  return response.json();
}

async function render() {
  const products = await fetchProducts();
  countLabel.textContent = `${products.length} items`;

  productsBody.innerHTML = "";
  for (const product of products) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${product.name}</td>
      <td>${formatCurrency(product.price)}</td>
      <td><input class="qty-input" type="number" min="0" value="${product.quantity}" /></td>
      <td>
        <div class="row-actions">
          <button class="secondary">Update Qty</button>
          <button class="danger">Delete</button>
        </div>
      </td>
    `;

    const qtyInput = tr.querySelector(".qty-input");
    const updateButton = tr.querySelector(".secondary");
    const deleteButton = tr.querySelector(".danger");

    updateButton.addEventListener("click", async () => {
      const quantity = Number(qtyInput.value);
      if (!Number.isInteger(quantity) || quantity < 0) {
        alert("Quantity must be a non-negative integer.");
        return;
      }
      await fetch(`/api/products/${product.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quantity }),
      });
      await render();
    });

    deleteButton.addEventListener("click", async () => {
      await fetch(`/api/products/${product.id}`, { method: "DELETE" });
      await render();
    });

    productsBody.appendChild(tr);
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const name = document.getElementById("name").value.trim();
  const quantity = Number(document.getElementById("quantity").value);
  const price = Number(document.getElementById("price").value);

  if (!name || !Number.isInteger(quantity) || quantity < 0 || Number.isNaN(price) || price < 0) {
    alert("Please provide a valid name, quantity, and price.");
    return;
  }

  await fetch("/api/products", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, quantity, price }),
  });

  form.reset();
  await render();
});

render();
