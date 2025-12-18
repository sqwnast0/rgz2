// Функции для работы с товарами (добавить в существующий app.js)

/**
 * Добавить товар в корзину через модальное окно
 */
async function addToCartModal(productId, productName, availableQuantity) {
    // Создаем модальное окно если его нет
    let modal = document.getElementById('addToCartModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'addToCartModal';
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Добавить в корзину</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <form>
                            <div class="mb-3">
                                <label class="form-label">Товар</label>
                                <p class="form-control-plaintext" id="modal-product-name"></p>
                            </div>
                            <div class="mb-3">
                                <label for="modal-quantity" class="form-label">Количество</label>
                                <div class="d-flex align-items-center">
                                    <input type="number" class="form-control me-3" id="modal-quantity" 
                                           value="1" min="1" max="${availableQuantity}" style="width: 100px;">
                                    <span class="text-muted">Доступно: <span id="modal-available">${availableQuantity}</span> шт</span>
                                </div>
                                <input type="hidden" id="modal-product-id">
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Отмена</button>
                        <button type="button" class="btn btn-primary" id="modal-add-to-cart-btn">
                            <i class="bi bi-cart-plus"></i> Добавить в корзину
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        
        // Обработчик кнопки
        document.getElementById('modal-add-to-cart-btn').onclick = confirmAddToCart;
        
        // Обработчик Enter
        modal.addEventListener('keypress', function(e) {
            if (e.which === 13) { // Enter key
                e.preventDefault();
                confirmAddToCart();
            }
        });
    }
    
    // Заполняем данные
    document.getElementById('modal-product-name').textContent = productName;
    document.getElementById('modal-product-id').value = productId;
    document.getElementById('modal-quantity').value = 1;
    document.getElementById('modal-quantity').max = availableQuantity;
    document.getElementById('modal-available').textContent = availableQuantity;
    
    // Показываем модальное окно
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

/**
 * Подтверждение добавления в корзину
 */
async function confirmAddToCart() {
    const productId = parseInt(document.getElementById('modal-product-id').value);
    const quantity = parseInt(document.getElementById('modal-quantity').value);
    
    try {
        await callApi('add_to_cart', {
            product_id: productId,
            quantity: quantity
        });
        
        showToast('Товар добавлен в корзину', 'success');
        
        // Закрываем модальное окно
        const modal = bootstrap.Modal.getInstance(document.getElementById('addToCartModal'));
        modal.hide();
        
        // Обновляем счетчик корзины
        updateCartBadge();
        
    } catch (error) {
        showToast('Ошибка при добавлении в корзину: ' + error.message, 'danger');
    }
}

/**
 * Создать заказ из корзины
 */
async function createOrder(notes = '') {
    try {
        const result = await callApi('create_order', { notes: notes });
        
        showToast(`Заказ ${result.order.order_number} создан успешно`, 'success');
        
        // Очищаем корзину
        await callApi('clear_cart');
        updateCartBadge();
        
        // Перенаправляем на страницу заказов
        window.location.href = '/orders';
        
    } catch (error) {
        showToast('Ошибка при создании заказа: ' + error.message, 'danger');
    }
}

/**
 * Обновить статус заказа (оплатить)
 */
async function updateOrderStatus(orderId, status) {
    try {
        await callApi('update_order_status', {
            order_id: orderId,
            status: status
        });
        
        const statusText = status === 'paid' ? 'оплачен' : 'не оплачен';
        showToast(`Статус заказа изменен на "${statusText}"`, 'success');
        
        // Обновляем список заказов если находимся на странице заказов
        if (typeof loadOrders === 'function') {
            loadOrders();
        }
        
    } catch (error) {
        showToast('Ошибка при обновлении статуса: ' + error.message, 'danger');
    }
}

/**
 * Отметить заказ как оплаченный (с подтверждением)
 */
function markOrderAsPaid(orderId, orderNumber) {
    if (confirm(`Отметить заказ ${orderNumber} как оплаченный?\nКоличество товаров на складе будет уменьшено.`)) {
        updateOrderStatus(orderId, 'paid');
    }
}

/**
 * Обновить счетчик корзины
 */
async function updateCartBadge() {
    try {
        const cartData = await callApi('get_cart');
        const badge = document.getElementById('cart-badge');
        
        if (badge && cartData.total_count > 0) {
            badge.textContent = cartData.total_count;
            badge.style.display = 'inline';
        } else if (badge) {
            badge.style.display = 'none';
        }
        
    } catch (error) {
        // Игнорируем ошибки при обновлении счетчика
    }
}