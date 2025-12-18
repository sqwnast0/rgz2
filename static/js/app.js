// ============================================
// Глобальные переменные и константы
// ============================================

let currentPage = 1;
const ITEMS_PER_PAGE = 20;

// ============================================
// API клиент для работы с JSON-RPC 2.0
// ============================================

async function callAPI(method, params = {}) {
    console.log(`API call: ${method}`, params);
    
    try {
        const requestId = Date.now(); // уникальный ID для запроса
        
        const response = await fetch('/api', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            credentials: 'same-origin',
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: method,
                params: params,
                id: requestId
            })
        });
        
        console.log(`API response status: ${response.status}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ошибка! Статус: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('API response:', result);
        
        // Проверка на ошибки JSON-RPC
        if (result.error) {
            console.error('JSON-RPC Ошибка:', result.error);
            throw new Error(result.error.message || 'Ошибка API');
        }
        
        return result.result;
        
    } catch (error) {
        console.error('Ошибка вызова API:', error);
        showNotification('Ошибка: ' + error.message, 'error');
        throw error;
    }
}

// ============================================
// Функции для работы с товарами
// ============================================

async function loadProducts(page = 1, categoryId = null, search = '') {
    try {
        const params = {
            page: page,
            per_page: ITEMS_PER_PAGE
        };
        
        if (categoryId && categoryId !== 'all') {
            params.category_id = parseInt(categoryId);
        }
        
        if (search) {
            params.search = search;
        }
        
        const result = await callAPI('get_products', params);
        currentPage = page;
        
        return result;
        
    } catch (error) {
        console.error('Ошибка загрузки товаров:', error);
        return {
            products: [],
            total: 0,
            pages: 0,
            current_page: 1
        };
    }
}

async function addOrUpdateProduct(productData) {
    try {
        const result = await callAPI('add_product', productData);
        showNotification(result.action === 'created' ? 
            'Товар успешно создан!' : 
            'Количество товара увеличено!', 'success');
        return result;
    } catch (error) {
        console.error('Ошибка добавления товара:', error);
        return null;
    }
}

async function deleteProduct(productId) {
    if (!confirm('Вы уверены, что хотите удалить этот товар?')) {
        return false;
    }
    
    try {
        await callAPI('delete_product', { product_id: productId });
        showNotification('Товар успешно удален!', 'success');
        return true;
    } catch (error) {
        console.error('Ошибка удаления товара:', error);
        return false;
    }
}

async function searchProducts(query) {
    try {
        const result = await callAPI('search_products', { query: query });
        return result.products;
    } catch (error) {
        console.error('Ошибка поиска товаров:', error);
        return [];
    }
}

// ============================================
// Функции для работы с корзиной
// ============================================

async function addToCart(productId, quantity = 1) {
    try {
        const result = await callAPI('add_to_cart', {
            product_id: parseInt(productId),
            quantity: parseInt(quantity)
        });
        
        showNotification('Товар добавлен в корзину!', 'success');
        
        // Обновляем счетчик корзины в навигации
        updateCartCounter();
        
        return result;
        
    } catch (error) {
        console.error('Ошибка добавления в корзину:', error);
        return null;
    }
}

async function removeFromCart(productId) {
    try {
        const result = await callAPI('remove_from_cart', {
            product_id: parseInt(productId)
        });
        
        showNotification('Товар удален из корзины', 'info');
        
        // Обновляем счетчик корзины
        updateCartCounter();
        
        return result;
        
    } catch (error) {
        console.error('Ошибка удаления из корзины:', error);
        return null;
    }
}

async function getCart() {
    try {
        const cart = await callAPI('get_cart');
        return cart;
    } catch (error) {
        console.error('Ошибка загрузки корзины:', error);
        return { items: [], total_items: 0, total_amount: 0 };
    }
}

async function updateCartItem(productId, quantity) {
    try {
        // Сначала удаляем, потом добавляем с новым количеством
        await removeFromCart(productId);
        if (quantity > 0) {
            await addToCart(productId, quantity);
        }
        return true;
    } catch (error) {
        console.error('Ошибка обновления корзины:', error);
        return false;
    }
}

async function clearCart() {
    if (!confirm('Очистить всю корзину?')) {
        return false;
    }
    
    try {
        await callAPI('clear_cart', {});
        showNotification('Корзина очищена', 'info');
        
        // Обновляем счетчик корзины
        updateCartCounter();
        
        return true;
    } catch (error) {
        console.error('Ошибка очистки корзины:', error);
        return false;
    }
}

async function updateCartCounter() {
    try {
        const cart = await getCart();
        const cartCounter = document.getElementById('cart-counter');
        if (cartCounter) {
            cartCounter.textContent = cart.total_items || '0';
            cartCounter.style.display = cart.total_items > 0 ? 'inline' : 'none';
        }
    } catch (error) {
        console.error('Ошибка обновления счетчика корзины:', error);
    }
}

// ============================================
// Функции для работы с заказами
// ============================================

async function createOrder(notes = '') {
    try {
        const result = await callAPI('create_order', { notes: notes });
        showNotification(`Заказ ${result.order.order_number} успешно создан!`, 'success');
        
        // Обновляем счетчик корзины
        updateCartCounter();
        
        return result;
        
    } catch (error) {
        console.error('Ошибка создания заказа:', error);
        return null;
    }
}

async function loadOrders(page = 1, status = null) {
    try {
        const params = {
            page: page,
            per_page: ITEMS_PER_PAGE
        };
        
        if (status) {
            params.status = status;
        }
        
        const result = await callAPI('get_orders', params);
        return result;
        
    } catch (error) {
        console.error('Ошибка загрузки заказов:', error);
        return {
            orders: [],
            total: 0,
            pages: 0,
            current_page: 1
        };
    }
}

async function markOrderPaid(orderId) {
    if (!confirm('Отметить заказ как оплаченный?')) {
        return false;
    }
    
    try {
        const result = await callAPI('mark_order_paid', { order_id: orderId });
        showNotification('Заказ отмечен как оплаченный!', 'success');
        return result;
    } catch (error) {
        console.error('Ошибка обновления заказа:', error);
        return null;
    }
}

async function updateOrderStatus(orderId, status) {
    try {
        const result = await callAPI('update_order_status', {
            order_id: orderId,
            status: status
        });
        showNotification('Статус заказа обновлен!', 'success');
        return result;
    } catch (error) {
        console.error('Ошибка обновления статуса заказа:', error);
        return null;
    }
}

// ============================================
// Функции для работы с категориями
// ============================================

async function loadCategories() {
    try {
        const categories = await callAPI('get_categories');
        return categories;
    } catch (error) {
        console.error('Ошибка загрузки категорий:', error);
        return [];
    }
}

// ============================================
// Функции для статистики
// ============================================

async function loadStatistics() {
    try {
        const stats = await callAPI('get_statistics');
        return stats;
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        return null;
    }
}

// ============================================
// Вспомогательные функции
// ============================================

function showNotification(message, type = 'info') {
    // Удаляем предыдущие уведомления
    document.querySelectorAll('.notification').forEach(n => n.remove());
    
    // Создаем элемент уведомления
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-content">${message}</div>
        <button class="notification-close">&times;</button>
    `;
    
    // Добавляем стили
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#4CAF50' : type === 'error' ? '#f44336' : type === 'warning' ? '#ff9800' : '#2196F3'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        display: flex;
        justify-content: space-between;
        align-items: center;
        min-width: 300px;
        max-width: 500px;
        animation: slideIn 0.3s ease-out;
    `;
    
    // Добавляем анимацию
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);
    
    // Кнопка закрытия
    const closeBtn = notification.querySelector('.notification-close');
    closeBtn.style.cssText = `
        background: none;
        border: none;
        color: white;
        font-size: 20px;
        cursor: pointer;
        margin-left: 15px;
        padding: 0;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        transition: background 0.2s;
    `;
    
    closeBtn.addEventListener('mouseover', () => {
        closeBtn.style.background = 'rgba(255,255,255,0.2)';
    });
    
    closeBtn.addEventListener('mouseout', () => {
        closeBtn.style.background = 'none';
    });
    
    closeBtn.addEventListener('click', () => {
        notification.style.animation = 'slideIn 0.3s ease-out reverse';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 300);
    });
    
    // Добавляем в DOM
    document.body.appendChild(notification);
    
    // Автоматическое удаление через 5 секунд
    setTimeout(() => {
        if (notification.parentNode) {
            notification.style.animation = 'slideIn 0.3s ease-out reverse';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.remove();
                }
            }, 300);
        }
    }, 5000);
}

function formatPrice(price) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 0,
        maximumFractionDigits: 2
    }).format(price);
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ============================================
// Инициализация при загрузке страницы
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('Warehouse Management System loaded');
    
    // Инициализация счетчика корзины
    updateCartCounter();
    
    // Обработка добавления товаров в корзину
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('add-to-cart-btn')) {
            e.preventDefault();
            const productId = e.target.dataset.productId;
            const quantityInput = document.querySelector(`#quantity-${productId}`);
            const quantity = quantityInput ? parseInt(quantityInput.value) : 1;
            
            if (productId) {
                addToCart(productId, quantity);
            }
        }
    });
    
    // Обработка удаления из корзины
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-from-cart-btn')) {
            e.preventDefault();
            const productId = e.target.dataset.productId;
            if (productId && confirm('Удалить товар из корзины?')) {
                removeFromCart(productId).then(() => {
                    // Перезагружаем страницу корзины
                    if (window.location.pathname.includes('/cart')) {
                        location.reload();
                    }
                });
            }
        }
    });
    
    // Обработка оформления заказа
    const checkoutBtn = document.getElementById('checkout-btn');
    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', function(e) {
            e.preventDefault();
            const notes = document.getElementById('order-notes')?.value || '';
            
            createOrder(notes).then(result => {
                if (result) {
                    // Перенаправляем на страницу заказов
                    setTimeout(() => {
                        window.location.href = '/orders';
                    }, 1500);
                }
            });
        });
    }
    
    // Обработка пометки заказа как оплаченного
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('mark-paid-btn')) {
            e.preventDefault();
            const orderId = e.target.dataset.orderId;
            if (orderId) {
                markOrderPaid(orderId).then(() => {
                    // Перезагружаем страницу заказов
                    if (window.location.pathname.includes('/orders')) {
                        location.reload();
                    }
                });
            }
        }
    });
    
    // Обработка очистки корзины
    const clearCartBtn = document.getElementById('clear-cart-btn');
    if (clearCartBtn) {
        clearCartBtn.addEventListener('click', function(e) {
            e.preventDefault();
            clearCart().then(() => {
                if (window.location.pathname.includes('/cart')) {
                    location.reload();
                }
            });
        });
    }
    
    // Обработка поиска товаров
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const searchInput = document.getElementById('search-input');
            if (searchInput && searchInput.value.trim()) {
                const searchTerm = searchInput.value.trim();
                window.location.href = `/products?search=${encodeURIComponent(searchTerm)}`;
            }
        });
    }
    
    // Обработка фильтрации по категориям
    const categoryFilter = document.getElementById('category-filter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', function() {
            const categoryId = this.value;
            const currentUrl = new URL(window.location.href);
            
            if (categoryId === 'all') {
                currentUrl.searchParams.delete('category');
            } else {
                currentUrl.searchParams.set('category', categoryId);
            }
            
            window.location.href = currentUrl.toString();
        });
    }
    
    // Проверка здоровья API при загрузке
    fetch('/api/health')
        .then(response => response.json())
        .then(data => {
            console.log('API Health:', data);
        })
        .catch(error => {
            console.error('API Health check failed:', error);
        });
});