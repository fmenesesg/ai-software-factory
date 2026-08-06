async function loadInventory() {
  const res = await fetch("/api/v1/inventory");
  const data = await res.json();
  const list = document.getElementById("inventory");
  const select = document.getElementById("sku");
  list.innerHTML = "";
  select.innerHTML = "";
  for (const item of data.items || []) {
    const li = document.createElement("li");
    li.textContent = `${item.sku} — ${item.name} (${item.quantity} in stock)`;
    list.appendChild(li);
    const opt = document.createElement("option");
    opt.value = item.sku;
    opt.textContent = item.sku;
    select.appendChild(opt);
  }
}

document.getElementById("order-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const sku = document.getElementById("sku").value;
  const quantity = Number(document.getElementById("quantity").value);
  const message = document.getElementById("message");
  const res = await fetch("/api/v1/orders", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sku, quantity }),
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    message.textContent = body.detail || "Order failed";
    return;
  }
  message.textContent = `Order #${body.order.id} created`;
  await loadInventory();
});

loadInventory().catch((err) => {
  document.getElementById("message").textContent = String(err);
});
